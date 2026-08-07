from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageColor import getrgb

from src.core.io_utils import load_json, load_script
from src.core.step import Step
from src.utils.config import Config


def _load_presets() -> List[Dict]:
    data = Config.load().steps.thumbnail.model_dump()
    items = data.get("palettes") or data.get("presets") or []
    return [dict(item) for item in items if isinstance(item, dict)]


PRESETS = _load_presets()


def _palette_candidates(config: Dict | None) -> List[Dict]:
    if not config:
        return PRESETS
    raw = config.get("palettes") or config.get("presets")
    if isinstance(raw, list):
        candidates = [item for item in raw if isinstance(item, dict)]
        if candidates:
            return candidates
    return PRESETS


class ThumbnailGenerator(Step):
    name = "generate_thumbnail"
    output_filename = "thumbnail.png"
    is_required = False

    def __init__(self, run_id: str, run_dir: Path, thumbnail_config: Dict | None = None) -> None:
        super().__init__(run_id, run_dir)
        cfg = dict(thumbnail_config or {})
        if cfg.get("randomize_palette", True):
            candidates = _palette_candidates(cfg)
            if candidates:
                cfg.update(random.choice(candidates))
        self.enabled = bool(cfg.get("enabled", True))
        self.width = int(cfg.get("width", 1280))
        self.height = int(cfg.get("height", 720))
        self.background_color = str(cfg.get("background_color", "#fef155"))
        self.title_color = str(cfg.get("title_color", "#EB001B"))
        self.subtitle_color = str(cfg.get("subtitle_color", "#EB001B"))
        self.show_subtitle = bool(cfg.get("show_subtitle", False))
        self.padding = int(cfg.get("padding", 80))
        self.safe_margin_pct = float(cfg.get("safe_margin_pct", 9.0))
        self.title_height_min_pct = float(cfg.get("title_height_min_pct", 30.0))
        self.title_height_max_pct = float(cfg.get("title_height_max_pct", 40.0))
        self.preview_width = int(cfg.get("preview_width", 200))
        self.title_font_size = int(cfg.get("title_font_size", 360))
        self.subtitle_font_size = int(cfg.get("subtitle_font_size", 56))
        self.max_lines = int(cfg.get("max_lines", 4))
        self.max_chars_per_line = int(cfg.get("max_chars_per_line", 12))
        self.font_path = cfg.get("font_path")
        self.overlay_configs = list(cfg.get("overlays", []))
        self.right_guard_band_px = int(cfg.get("right_guard_band_px", 0))
        self.outline_inner_color = str(cfg.get("outline_inner_color", "#FFFFFF"))
        self.outline_inner_width = int(cfg.get("outline_inner_width", 3))
        self.outline_outer_color = str(cfg.get("outline_outer_color", "#000000"))
        self.outline_outer_width = int(cfg.get("outline_outer_width", 6))

    def execute(self, inputs: Dict[str, Path | str]) -> Path:
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.enabled:
            output_path.touch(exist_ok=True)
            return output_path

        script = load_script(Path(inputs["generate_script"]))
        metadata = load_json(Path(inputs["analyze_metadata"])) if inputs.get("analyze_metadata") else None
        title = self._resolve_title(metadata, script)
        subtitle = self._resolve_subtitle(metadata, script)

        bg_rgb = getrgb(self.background_color) + (255,)
        image = Image.new("RGBA", (self.width, self.height), color=bg_rgb)
        draw = ImageDraw.Draw(image)
        margin_x, margin_y = self._safe_margins()
        text_right = self.width - margin_x - max(0, self.right_guard_band_px)
        max_title_height = int(self.height * self.title_height_max_pct / 100)
        title_font, actual_font_size = self._fit_title_font(title, text_right - margin_x, max_title_height)
        title_bottom = self._render_text(
            draw,
            title,
            title_font,
            self.title_color,
            margin_y,
            text_right,
            left_edge=margin_x,
        )
        title_height_pct = 100 * max(0, title_bottom - margin_y) / self.height

        if self.show_subtitle and subtitle:
            subtitle_font = self._load_font(self.subtitle_font_size)
            y_offset = title_bottom + max(8, margin_y // 2)
            self._render_text(
                draw,
                subtitle,
                subtitle_font,
                self.subtitle_color,
                y_offset,
                text_right,
                left_edge=margin_x,
            )

        for overlay in self._prepare_overlays():
            image.paste(overlay["image"], overlay["position"], mask=overlay["image"])

        rgb_image = image.convert("RGB")
        rgb_image.save(output_path, format="PNG")
        self._save_preview(rgb_image, output_path)
        self._save_metadata(output_path, title, actual_font_size, title_height_pct)
        return output_path

    def _resolve_title(self, metadata: Dict | None, script) -> str:
        if metadata and metadata.get("title"):
            return str(metadata["title"]).strip()
        return script.segments[0].text.strip() if script.segments else "最新ニュース"

    def _resolve_subtitle(self, metadata: Dict | None, script) -> str:
        if metadata:
            desc = str(metadata.get("description", "")).strip()
            if desc:
                return desc.split("\n", 1)[0][:80] or "解説付き"
        if len(script.segments) > 1:
            return script.segments[1].text.strip() or "解説付き"
        return script.segments[0].speaker.strip() if script.segments else "解説付き"

    def _safe_margins(self) -> Tuple[int, int]:
        pct = max(0.0, min(49.0, self.safe_margin_pct)) / 100
        return round(self.width * pct), round(self.height * pct)

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        if self.font_path:
            font_file = Path(self.font_path)
            if font_file.exists():
                return ImageFont.truetype(str(font_file), size)
        return ImageFont.load_default(size=size)

    def _fit_title_font(
        self, text: str, max_width: int, max_height: int
    ) -> tuple[ImageFont.ImageFont, int]:
        max_size = max(24, self.title_font_size)
        for size in range(max_size, 23, -4):
            font = self._load_font(size)
            lines = self._wrap_text(text, font, max_width)
            if self._text_block_height(font, lines) <= max_height:
                return font, size
        return self._load_font(24), 24

    def _text_block_height(self, font: ImageFont.ImageFont, lines: List[str]) -> int:
        if not lines:
            return 0
        heights = []
        for line in lines:
            bbox = font.getbbox(line or " ")
            heights.append(max(1, int(bbox[3] - bbox[1])))
        spacing = max(4, self.padding // 4)
        return sum(heights) + spacing * max(0, len(lines) - 1)

    def _prepare_overlays(self) -> List[Dict]:
        overlays = []
        for cfg in self.overlay_configs:
            if not cfg.get("enabled", True):
                continue
            image_path = Path(str(cfg.get("image_path", "")))
            if not image_path.exists():
                continue
            with Image.open(image_path) as img:
                overlay = img.convert("RGBA")
            overlay = self._scale_overlay(overlay, cfg)
            overlays.append({"image": overlay, "position": self._resolve_position(overlay.size, cfg)})
        return overlays

    def _scale_overlay(self, overlay: Image.Image, cfg: Dict) -> Image.Image:
        w, h = overlay.size
        if cfg.get("height"):
            h = int(cfg["height"])
            w = int(w * h / overlay.size[1])
        elif cfg.get("width"):
            w = int(cfg["width"])
            h = int(h * w / overlay.size[0])
        elif cfg.get("height_ratio"):
            h = int(self.height * float(cfg["height_ratio"]))
            w = int(w * h / overlay.size[1])
        elif cfg.get("width_ratio"):
            w = int(self.width * float(cfg["width_ratio"]))
            h = int(h * w / overlay.size[0])
        if (w, h) == overlay.size:
            return overlay
        return overlay.resize((max(1, w), max(1, h)), Image.Resampling.LANCZOS)

    def _resolve_position(self, size: Tuple[int, int], cfg: Dict) -> Tuple[int, int]:
        anchor = str(cfg.get("anchor", "bottom_right")).lower()
        offset = cfg.get("offset") or {}
        w, h = size
        top, right, bottom, left = (int(offset.get(k) or 0) for k in ("top", "right", "bottom", "left"))
        if "left" in anchor:
            x = left
        elif "right" in anchor:
            x = self.width - w - right
        else:
            x = (self.width - w) // 2 + left - right
        if "top" in anchor:
            y = top
        elif "bottom" in anchor:
            y = self.height - h - bottom
        else:
            y = (self.height - h) // 2 + top - bottom
        return max(0, min(self.width - w, x)), max(0, min(self.height - h, y))

    def _render_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
        color: str,
        top: int,
        right_edge: int,
        *,
        left_edge: int | None = None,
    ) -> int:
        x = self.padding if left_edge is None else left_edge
        max_width = max(1, right_edge - x)
        lines = self._wrap_text(text, font, max_width)
        y = top
        for i, line in enumerate(lines):
            draw.text(
                (x, y),
                line,
                fill=self.outline_outer_color,
                font=font,
                stroke_width=self.outline_outer_width,
                stroke_fill=self.outline_outer_color,
            )
            draw.text(
                (x, y),
                line,
                fill=self.outline_inner_color,
                font=font,
                stroke_width=self.outline_inner_width,
                stroke_fill=self.outline_inner_color,
            )
            draw.text((x, y), line, fill=color, font=font)
            bbox = draw.textbbox((x, y), line, font=font)
            y = bbox[3] + (max(4, self.padding // 4) if i < len(lines) - 1 else 0)
        return y

    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        lines = []
        for chunk in text.split("\n"):
            if len(lines) >= self.max_lines:
                break
            chunk = chunk.strip()
            if not chunk:
                continue
            current = ""
            for char in chunk:
                tentative = current + char
                if self._text_width(font, tentative) <= max_width and len(tentative) <= self.max_chars_per_line:
                    current = tentative
                else:
                    if current:
                        lines.append(current)
                        if len(lines) >= self.max_lines:
                            return lines
                    current = char
            if current and len(lines) < self.max_lines:
                lines.append(current)
        return lines[: self.max_lines] if lines else [text[: self.max_chars_per_line] if text else ""]

    def _text_width(self, font: ImageFont.ImageFont, text: str) -> int:
        if hasattr(font, "getlength"):
            return int(font.getlength(text))
        bbox = font.getbbox(text)
        return int(bbox[2] - bbox[0])

    def _save_preview(self, image: Image.Image, output_path: Path) -> Path:
        width = max(1, min(self.width, self.preview_width))
        height = max(1, round(self.height * width / self.width))
        preview_path = output_path.with_name(f"{output_path.stem}.preview.png")
        image.resize((width, height), Image.Resampling.LANCZOS).save(preview_path, format="PNG")
        return preview_path

    def _save_metadata(self, output_path: Path, title: str, font_size: int, title_height_pct: float) -> Path:
        metadata_path = output_path.with_name(f"{output_path.stem}.metadata.json")
        payload = {
            "copy": title,
            "font_size_main": font_size,
            "outline_white_px": self.outline_inner_width,
            "outline_black_px": self.outline_outer_width,
            "safe_margin_pct": self.safe_margin_pct,
            "background_color": self.background_color,
            "text_color": self.title_color,
            "preview_width_px": max(1, min(self.width, self.preview_width)),
            "title_height_pct": round(title_height_pct, 2),
            "title_height_target_pct": [self.title_height_min_pct, self.title_height_max_pct],
        }
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return metadata_path
