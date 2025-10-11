from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from PIL import Image, ImageDraw, ImageFont

from src.models import Script
from src.steps.base import Step


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
        self.font_path = cfg.get("font_path")

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

        image = Image.new("RGB", (self.width, self.height), color=self.background_color)
        draw = ImageDraw.Draw(image)

        title_font = self._load_font(self.title_font_size)
        subtitle_font = self._load_font(self.subtitle_font_size)

        title_y = self.padding
        draw.text((self.padding, title_y), title, fill=self.title_color, font=title_font)

        subtitle_y = title_y + self.title_font_size + self.padding // 2
        draw.text((self.padding, subtitle_y), subtitle, fill=self.subtitle_color, font=subtitle_font)

        image.save(output_path, format="PNG")
        return output_path

    def _load_script(self, path: Path) -> Script:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)

    def _load_metadata(self, path: Path) -> Dict:
        if not path.exists():
            return {}
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
            recommendations = metadata.get("recommendations") or []
            if recommendations:
                return str(recommendations[0]).strip()
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
