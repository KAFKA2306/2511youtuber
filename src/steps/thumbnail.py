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
        overlays_cfg = cfg.get("overlays") or []
        self.overlays: List[Dict] = []
        for overlay_cfg in overlays_cfg:
            normalized = self._normalize_overlay_config(overlay_cfg)
            if normalized:
                self.overlays.append(normalized)

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

        if self.overlays:
            image = self._apply_overlays(image)

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
            tags = metadata.get("tags") or []
            for tag in tags:
                if not isinstance(tag, str):
                    continue
                clean = tag.strip()
                if clean:
                    keywords.append(clean)
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

    def _normalize_overlay_config(self, data: Dict) -> Dict | None:
        if not isinstance(data, dict):
            return None
        path = data.get("image_path") or data.get("path")
        if not path:
            return None
        overlay: Dict = {
            "enabled": bool(data.get("enabled", True)),
            "path": str(path),
            "anchor": str(data.get("anchor", "bottom_right")),
        }
        if "height_ratio" in data and data["height_ratio"] is not None:
            overlay["height_ratio"] = float(data["height_ratio"])
        if "width_ratio" in data and data["width_ratio"] is not None:
            overlay["width_ratio"] = float(data["width_ratio"])
        if "height" in data and data["height"] is not None:
            overlay["height"] = int(data["height"])
        if "width" in data and data["width"] is not None:
            overlay["width"] = int(data["width"])
        offsets = data.get("offset") or {}
        if isinstance(offsets, dict):
            overlay["offset"] = {
                "top": int(offsets.get("top", 0) or 0),
                "right": int(offsets.get("right", 0) or 0),
                "bottom": int(offsets.get("bottom", 0) or 0),
                "left": int(offsets.get("left", 0) or 0),
            }
        return overlay

    def _apply_overlays(self, base_image: Image.Image) -> Image.Image:
        result = base_image.convert("RGBA")
        applied = False
        for overlay in self.overlays:
            if not overlay.get("enabled", True):
                continue
            path = Path(overlay["path"])
            if not path.exists():
                self.logger.warning("Overlay file not found", overlay=str(path))
                continue
            with Image.open(path) as overlay_image:
                overlay_rgba = overlay_image.convert("RGBA")
            resized = self._resize_overlay(overlay_rgba, overlay)
            position = self._calculate_overlay_position(resized.size, overlay)
            result.paste(resized, position, resized)
            applied = True
        if not applied:
            return base_image
        return result.convert("RGB")

    def _resize_overlay(self, overlay_image: Image.Image, overlay: Dict) -> Image.Image:
        width, height = overlay_image.size
        target_width = overlay.get("width")
        target_height = overlay.get("height")
        height_ratio = overlay.get("height_ratio")
        width_ratio = overlay.get("width_ratio")
        if height_ratio:
            target_height = int(self.height * float(height_ratio))
        if width_ratio:
            target_width = int(self.width * float(width_ratio))
        if target_height and not target_width:
            scale = target_height / height
            target_width = int(width * scale)
        if target_width and not target_height:
            scale = target_width / width
            target_height = int(height * scale)
        if not target_width or not target_height:
            return overlay_image
        target_width = max(1, int(target_width))
        target_height = max(1, int(target_height))
        return overlay_image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    def _calculate_overlay_position(self, overlay_size: tuple[int, int], overlay: Dict) -> tuple[int, int]:
        overlay_width, overlay_height = overlay_size
        anchor = overlay.get("anchor", "bottom_right")
        offsets = overlay.get("offset") or {}
        top = int(offsets.get("top", 0))
        right = int(offsets.get("right", 0))
        bottom = int(offsets.get("bottom", 0))
        left = int(offsets.get("left", 0))
        if anchor == "top_left":
            x = left
            y = top
        elif anchor == "top_right":
            x = self.width - overlay_width - right
            y = top
        elif anchor == "bottom_left":
            x = left
            y = self.height - overlay_height - bottom
        else:
            x = self.width - overlay_width - right
            y = self.height - overlay_height - bottom
        return int(x), int(y)
