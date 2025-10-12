from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from src.core.step import Step
from src.models import Script


class ThumbnailGenerator(Step):
    name = "generate_thumbnail"
    output_filename = "thumbnail.png"
    is_required = False

    def __init__(self, run_id: str, run_dir: Path, thumbnail_config: Dict | None = None) -> None:
        super().__init__(run_id, run_dir)
        cfg = thumbnail_config or {}
        self.enabled = bool(cfg.get("enabled", True))
        self.width = int(cfg.get("width", 1280))
        self.height = int(cfg.get("height", 720))
        self.background_color = str(cfg.get("background_color", "#1a2238"))
        self.title_color = str(cfg.get("title_color", "#FFFFFF"))
        self.subtitle_color = str(cfg.get("subtitle_color", "#FFD166"))
        self.padding = int(cfg.get("padding", 80))
        self.title_font_size = int(cfg.get("title_font_size", 96))
        self.subtitle_font_size = int(cfg.get("subtitle_font_size", 56))
        self.max_lines = int(cfg.get("max_lines", 3))
        self.max_chars_per_line = int(cfg.get("max_chars_per_line", 12))
        self.font_path = cfg.get("font_path")
        self.overlay_configs = list(cfg.get("overlays", []))

    def execute(self, inputs: Dict[str, Path | str]) -> Path:
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.enabled:
            output_path.touch(exist_ok=True)
            return output_path

        script_path = Path(inputs["generate_script"])
        script = self._load_script(script_path)
        metadata_path = inputs.get("analyze_metadata")
        metadata = self._load_metadata(Path(metadata_path)) if metadata_path else None

        title = self._resolve_title(metadata, script)
        subtitle = self._resolve_subtitle(metadata, script)

        image = Image.new("RGBA", (self.width, self.height), color=self.background_color)
        draw = ImageDraw.Draw(image)

        overlays = self._prepare_overlays()
        title_font = self._load_font(self.title_font_size)
        subtitle_font = self._load_font(self.subtitle_font_size)

        text_right_edge = self.width - self.padding
        title_bottom = self._render_text_block(draw, title, title_font, self.title_color, self.padding, text_right_edge)
        self._render_text_block(
            draw,
            subtitle,
            subtitle_font,
            self.subtitle_color,
            title_bottom + self.padding // 2,
            text_right_edge,
        )

        for overlay in overlays:
            image.paste(overlay["image"], overlay["position"], mask=overlay["image"])
        image.convert("RGB").save(output_path, format="PNG")
        return output_path

    def _load_script(self, path: Path) -> Script:
        return Script(**self._read_json(path))

    def _load_metadata(self, path: Path) -> Dict:
        return self._read_json(path, default={})

    def _read_json(self, path: Path, default: Dict | None = None) -> Dict:
        if not path.exists():
            return default or {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _resolve_title(self, metadata: Dict | None, script: Script) -> str:
        if metadata and metadata.get("title"):
            return str(metadata["title"]).strip()
        if script.segments:
            return script.segments[0].text.strip() or "最新ニュース"
        return "最新ニュース"

    def _resolve_subtitle(self, metadata: Dict | None, script: Script) -> str:
        if metadata:
            description = str(metadata.get("description", "")).strip()
            if description:
                return description.split("\n", 1)[0][:80] or "解説付き"
        if len(script.segments) > 1:
            return script.segments[1].text.strip() or "解説付き"
        if script.segments:
            return script.segments[0].speaker.strip() or "解説付き"
        return "解説付き"

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        if self.font_path:
            font_file = Path(self.font_path)
            if font_file.exists():
                return ImageFont.truetype(str(font_file), size)
        return ImageFont.load_default()

    def _prepare_overlays(self) -> List[Dict]:
        overlays: List[Dict] = []
        for cfg in self.overlay_configs:
            if not cfg.get("enabled", True):
                continue
            image_path = Path(str(cfg.get("image_path", "")))
            if not image_path.exists():
                continue
            with Image.open(image_path) as overlay_image:
                overlay = overlay_image.convert("RGBA")
            overlay = self._scale_overlay(overlay, cfg)
            position = self._resolve_overlay_position(overlay.size, cfg)
            overlays.append(
                {
                    "image": overlay,
                    "position": position,
                }
            )
        return overlays

    def _scale_overlay(self, overlay: Image.Image, cfg: Dict) -> Image.Image:
        width, height = overlay.size
        target_width, target_height = width, height

        if cfg.get("height"):
            target_height = int(cfg["height"])
            scale = target_height / height
            target_width = int(width * scale)
        elif cfg.get("width"):
            target_width = int(cfg["width"])
            scale = target_width / width
            target_height = int(height * scale)
        elif cfg.get("height_ratio"):
            target_height = int(self.height * float(cfg["height_ratio"]))
            scale = target_height / height
            target_width = int(width * scale)
        elif cfg.get("width_ratio"):
            target_width = int(self.width * float(cfg["width_ratio"]))
            scale = target_width / width
            target_height = int(height * scale)

        target_size = (max(1, target_width), max(1, target_height))
        if target_size != overlay.size:
            return overlay.resize(target_size, Image.LANCZOS)
        return overlay

    def _resolve_overlay_position(self, size: Tuple[int, int], cfg: Dict) -> Tuple[int, int]:
        anchor = str(cfg.get("anchor", "bottom_right")).lower()
        offset = cfg.get("offset") or {}

        width, height = size
        top = int(offset.get("top") or 0)
        right = int(offset.get("right") or 0)
        bottom = int(offset.get("bottom") or 0)
        left = int(offset.get("left") or 0)

        if "left" in anchor:
            x = left
        elif "right" in anchor:
            x = self.width - width - right
        else:
            x = (self.width - width) // 2 + left - right

        if "top" in anchor:
            y = top
        elif "bottom" in anchor:
            y = self.height - height - bottom
        else:
            y = (self.height - height) // 2 + top - bottom

        x = max(0, min(self.width - width, x))
        y = max(0, min(self.height - height, y))
        return int(x), int(y)

    def _render_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
        color: str,
        top: int,
        right_edge: int,
    ) -> int:
        max_width = max(self.padding, right_edge - self.padding)
        lines = self._wrap_text(text, font, max_width)
        y = top
        for index, line in enumerate(lines):
            draw.text((self.padding, y), line, fill=color, font=font)
            bbox = draw.textbbox((self.padding, y), line, font=font)
            y = bbox[3]
            if index < len(lines) - 1:
                y += max(4, self.padding // 4)
        return y

    def _wrap_text(
        self,
        text: str,
        font: ImageFont.ImageFont | None = None,
        max_width: int | None = None,
        max_chars: int | None = None,
    ) -> List[str]:
        if font is None:
            font = self._load_font(self.title_font_size)
        if max_width is None:
            max_width = max(self.padding, self.width - (self.padding * 2))
        char_limit = max_chars if max_chars is not None else self.max_chars_per_line
        if max_width <= 0:
            return self._wrap_text_greedy(text, font, max_width, char_limit)

        lines: List[str] = []
        for chunk in text.split("\n"):
            if len(lines) >= self.max_lines:
                break
            chunk = chunk.strip()
            if not chunk:
                continue
            chunk_lines = self._wrap_text_greedy(chunk, font, max_width, char_limit)
            lines.extend(chunk_lines)
            if len(lines) >= self.max_lines:
                break

        if not lines:
            lines = self._wrap_text_greedy(text, font, max_width, char_limit)
        return lines[: self.max_lines]

    def _wrap_text_greedy(
        self,
        text: str,
        font: ImageFont.ImageFont,
        max_width: int,
        char_limit: int | None = None,
    ) -> List[str]:
        if char_limit is None:
            char_limit = self.max_chars_per_line
        if max_width <= 0:
            return [text[:char_limit]] if text else [""]

        lines: List[str] = []
        current = ""
        for char in text:
            if char == "\n":
                if current:
                    lines.append(current)
                    if len(lines) >= self.max_lines:
                        return lines[: self.max_lines]
                current = ""
                continue
            tentative = current + char
            if self._measure_text_width(font, tentative) <= max_width and len(tentative) <= char_limit:
                current = tentative
                continue
            if current:
                lines.append(current)
                if len(lines) >= self.max_lines:
                    return lines
            current = char
            if len(current) > char_limit or self._measure_text_width(font, current) > max_width:
                lines.append(current)
                current = ""
                if len(lines) >= self.max_lines:
                    return lines

        if current and len(lines) < self.max_lines:
            lines.append(current)

        if not lines:
            lines = [text[:char_limit]] if text else [""]
        return lines[: self.max_lines]

    def _measure_text_width(self, font: ImageFont.ImageFont, text: str) -> int:
        if hasattr(font, "getlength"):
            return int(font.getlength(text))
        bbox = font.getbbox(text)
        return int(bbox[2] - bbox[0])
