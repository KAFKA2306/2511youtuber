from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageColor import getrgb

from src.core.io_utils import load_json, load_script
from src.core.step import Step


def _get_thumbnail_preset() -> Dict:
    PRESET_A = {
        "background_color": "#fef155",
        "title_color": "#EB001B",
        "outline_inner_color": "#FFFFFF",
        "outline_inner_width": 30,
        "outline_outer_color": "#000000",
        "outline_outer_width": 0,
    }
    PRESET_B = {
        "background_color": "#000000",
        "title_color": "#FFD700",
        "outline_inner_color": "#EB001B",
        "outline_inner_width": 30,
        "outline_outer_color": "#000000",
        "outline_outer_width": 0,
    }
    PRESET_CALM_BLACK = {
        "background_color": "#0B0F19",
        "title_color": "#FFE16A",
        "outline_inner_color": "#FFFFFF",
        "outline_inner_width": 15,
        "outline_outer_color": "#000000",
        "outline_outer_width": 0,
    }
    PRESET_DEEP_CHARCOAL = {
        "background_color": "#111827",
        "title_color": "#FDE047",
        "outline_inner_color": "#FFFFFF",
        "outline_inner_width": 15,
        "outline_outer_color": "#0B0F19",
        "outline_outer_width": 0,
    }
    PRESET_DARK_NAVY_GOLD = {
        "background_color": "#0A0F1F",
        "title_color": "#FFD700",
        "outline_inner_color": "#FFFFFF",
        "outline_inner_width": 15,
        "outline_outer_color": "#000000",
        "outline_outer_width": 0,
    }
    return random.choice(
        [PRESET_A, PRESET_B, PRESET_CALM_BLACK, PRESET_DEEP_CHARCOAL, PRESET_DARK_NAVY_GOLD]
    )


class ThumbnailGenerator(Step):
    name = "generate_thumbnail"
    output_filename = "thumbnail.png"
    is_required = False

    def __init__(self, run_id: str, run_dir: Path, thumbnail_config: Dict | None = None) -> None:
        super().__init__(run_id, run_dir)
        preset = _get_thumbnail_preset()
        cfg = thumbnail_config or {}
        for key in preset:
            cfg.pop(key, None)
        cfg = {**cfg, **preset}
        self.enabled = bool(cfg.get("enabled", True))
        self.width = int(cfg.get("width", 1280))
        self.height = int(cfg.get("height", 720))
        self.background_color = str(cfg.get("background_color", "#1a2238"))
        self.title_color = str(cfg.get("title_color", "#FFFFFF"))
        self.subtitle_color = str(cfg.get("subtitle_color", "#FFD166"))
        self.show_subtitle = bool(cfg.get("show_subtitle", True))
        self.padding = int(cfg.get("padding", 80))
        self.title_font_size = int(cfg.get("title_font_size", 206))
        self.subtitle_font_size = int(cfg.get("subtitle_font_size", 56))
        self.max_lines = int(cfg.get("max_lines", 3))
        self.max_chars_per_line = int(cfg.get("max_chars_per_line", 12))
        self.font_path = cfg.get("font_path")
        self.overlay_configs = list(cfg.get("overlays", []))
        self.right_guard_band_px = int(cfg.get("right_guard_band_px", 0))
        self.outline_inner_color = str(cfg.get("outline_inner_color", "#EB001B"))
        self.outline_inner_width = int(cfg.get("outline_inner_width", 20))
        self.outline_outer_color = str(cfg.get("outline_outer_color", "#000000"))
        self.outline_outer_width = int(cfg.get("outline_outer_width", 20))

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
        title_font = self._load_font(self.title_font_size)
        subtitle_font = self._load_font(self.subtitle_font_size)
        text_right = self.width - self.padding - max(0, self.right_guard_band_px)
        title_bottom = self._render_text(draw, title, title_font, self.title_color, self.padding, text_right)
        if self.show_subtitle and subtitle:
            y_offset = title_bottom + self.padding // 2
            self._render_text(draw, subtitle, subtitle_font, self.subtitle_color, y_offset, text_right)

        for overlay in self._prepare_overlays():
            image.paste(overlay["image"], overlay["position"], mask=overlay["image"])
        image.convert("RGB").save(output_path, format="PNG")
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

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        if self.font_path:
            font_file = Path(self.font_path)
            if font_file.exists():
                return ImageFont.truetype(str(font_file), size)
        return ImageFont.load_default()

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
        return overlay.resize((max(1, w), max(1, h)), Image.LANCZOS) if (w, h) != overlay.size else overlay

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
        self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, color: str, top: int, right_edge: int
    ) -> int:
        max_width = max(self.padding, right_edge - self.padding)
        lines = self._wrap_text(text, font, max_width)
        y = top
        for i, line in enumerate(lines):
            x = self.padding
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
