from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Dict, List

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
        self.accent_color = str(cfg.get("accent_color", "#EF476F"))
        self.padding = int(cfg.get("padding", 80))
        self.max_lines = int(cfg.get("max_lines", 3))
        self.max_chars_per_line = int(cfg.get("max_chars_per_line", 12))
        self.title_font_size = int(cfg.get("title_font_size", 96))
        self.subtitle_font_size = int(cfg.get("subtitle_font_size", 56))
        self.font_path = cfg.get("font_path")
        self.icon_path = cfg.get("icon_path")
        self.icon_size = int(cfg.get("icon_size", 100))
        self.icon_position = str(cfg.get("icon_position", "bottom_right"))
        self.icon_margin = int(cfg.get("icon_margin", 40))

    def execute(self, inputs: Dict[str, Path | str]) -> Path:
        if not self.enabled:
            self.logger.info("Thumbnail generation disabled, skipping")
            output_path = self.get_output_path()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.touch(exist_ok=True)
            return output_path

        script_path = inputs.get("generate_script")
        if not script_path:
            raise ValueError("Script file not found for thumbnail generation")

        script_path = Path(script_path)
        if not script_path.exists():
            raise ValueError("Script file not found for thumbnail generation")

        metadata_path = inputs.get("analyze_metadata")
        metadata = None
        if metadata_path:
            metadata_candidate = Path(metadata_path)
            if metadata_candidate.exists():
                metadata = self._load_metadata(metadata_candidate)

        script = self._load_script(script_path)

        title_text = self._build_title_text(metadata, script)
        subtitle_text = self._build_subtitle_text(metadata, script)
        callouts = self._build_callouts(metadata, script)

        image = Image.new("RGB", (self.width, self.height), color=self.background_color)
        draw = ImageDraw.Draw(image)

        accent_width = max(self.padding // 4, 12)
        draw.rectangle([(0, 0), (accent_width, self.height)], fill=self.accent_color)

        title_font = self._load_font(self.title_font_size)
        subtitle_font = self._load_font(self.subtitle_font_size)
        callout_font_size = max(self.subtitle_font_size - 20, 32)
        callout_font = self._load_font(callout_font_size)

        text_x = accent_width + self.padding
        current_y = self.padding

        title_lines = self._wrap_text(title_text, self.max_chars_per_line)[: self.max_lines]
        if not title_lines:
            title_lines = ["金融ニュース速報"]

        for line in title_lines:
            draw.text((text_x, current_y), line, font=title_font, fill=self.title_color)
            current_y += self.title_font_size + 10

        subtitle_lines = self._wrap_text(subtitle_text, self.max_chars_per_line + 4)[: self.max_lines]
        if subtitle_lines:
            current_y += 20
            for line in subtitle_lines:
                draw.text((text_x, current_y), line, font=subtitle_font, fill=self.subtitle_color)
                current_y += self.subtitle_font_size + 8

        if callouts:
            callout_y = max(current_y + 20, self.height - self.padding - len(callouts) * (callout_font_size + 12))
            for callout in callouts[: self.max_lines]:
                text = f"・{callout}"
                draw.text((text_x, callout_y), text, font=callout_font, fill=self.subtitle_color)
                callout_y += callout_font_size + 12

        if self.icon_path:
            icon_composite = self._overlay_icon(image)
            if icon_composite:
                image = icon_composite

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG")
        self.logger.info("Thumbnail generated", output_path=str(output_path))
        return output_path

    def _load_script(self, path: Path) -> Script:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)

    def _load_metadata(self, path: Path) -> Dict:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        text = (text or "").replace("\n", " ").strip()
        if not text:
            return []
        wrapper = textwrap.TextWrapper(
            width=max(max_chars, 1),
            break_long_words=True,
            break_on_hyphens=False,
        )
        return wrapper.wrap(text)

    def _build_title_text(self, metadata: Dict | None, script: Script) -> str:
        if metadata:
            title = metadata.get("title")
            if title:
                return str(title)
        if script.segments:
            return script.segments[0].text
        return "金融ニュース速報"

    def _build_subtitle_text(self, metadata: Dict | None, script: Script) -> str:
        if metadata:
            recommendations = metadata.get("recommendations") or []
            if recommendations:
                return str(recommendations[0])
        if len(script.segments) >= 2:
            speakers = {segment.speaker for segment in script.segments[:2]}
            speaker_text = "・".join(sorted(speakers))
            return f"{speaker_text} が最新トレンドを解説"
        if script.segments:
            return f"{script.segments[0].speaker} が最新ニュースを解説"
        return "日本経済の動きをわかりやすく解説"

    def _build_callouts(self, metadata: Dict | None, script: Script) -> List[str]:
        keywords: List[str] = []
        if metadata:
            analysis = metadata.get("analysis") or {}
            density = analysis.get("keyword_density") or {}
            if isinstance(density, dict):
                ordered = sorted(
                    density.items(),
                    key=lambda item: item[1].get("density", 0),
                    reverse=True,
                )
                for keyword, stats in ordered:
                    if stats.get("count", 0) > 0:
                        keywords.append(str(keyword))
        if keywords:
            return [self._truncate(keyword, self.max_chars_per_line + 2) for keyword in keywords[: self.max_lines]]

        callouts: List[str] = []
        for segment in script.segments:
            snippet = segment.text.strip()
            if not snippet:
                continue
            callouts.append(self._truncate(snippet, self.max_chars_per_line + 4))
            if len(callouts) >= self.max_lines:
                break
        return callouts

    def _truncate(self, text: str, max_chars: int) -> str:
        text = text.strip()
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1] + "…"

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        candidates = [self.font_path] if self.font_path else []
        candidates += [
            "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
            "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
            "NotoSansCJKjp-Bold.otf",
            "NotoSansJP-Bold.otf",
            "NotoSans-Bold.ttf",
            "SourceHanSansJP-Bold.otf",
            "SourceHanSansJP-Regular.otf",
            "DejaVuSans-Bold.ttf",
            "DejaVuSans.ttf",
        ]
        for candidate in candidates:
            if not candidate:
                continue
            try:
                return ImageFont.truetype(candidate, size)
            except (OSError, IOError):
                continue
        self.logger.warning("Falling back to default PIL font; consider configuring thumbnail.font_path")
        return ImageFont.load_default()

    def _overlay_icon(self, base_image: Image.Image) -> Image.Image | None:
        icon_path = Path(self.icon_path)
        if not icon_path.exists():
            self.logger.warning("Icon file not found", icon_path=str(icon_path))
            return None

        icon = Image.open(str(icon_path)).convert("RGBA")
        icon = icon.resize((self.icon_size, self.icon_size), Image.Resampling.LANCZOS)

        x, y = self._calculate_icon_position()

        result = base_image.convert("RGBA")
        result.paste(icon, (x, y), icon)
        return result.convert("RGB")

    def _calculate_icon_position(self) -> tuple[int, int]:
        if self.icon_position == "bottom_right":
            x = self.width - self.icon_size - self.icon_margin
            y = self.height - self.icon_size - self.icon_margin
        elif self.icon_position == "bottom_left":
            x = self.icon_margin
            y = self.height - self.icon_size - self.icon_margin
        elif self.icon_position == "top_right":
            x = self.width - self.icon_size - self.icon_margin
            y = self.icon_margin
        elif self.icon_position == "top_left":
            x = self.icon_margin
            y = self.icon_margin
        else:
            x = self.width - self.icon_size - self.icon_margin
            y = self.height - self.icon_size - self.icon_margin
        return x, y
