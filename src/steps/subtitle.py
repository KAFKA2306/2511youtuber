from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageFont

from src.core.io_utils import load_script, validate_input_files, write_text
from src.core.media_utils import get_audio_duration
from src.core.step import Step


class SubtitleFormatter(Step):
    name = "prepare_subtitles"
    output_filename = "subtitles.srt"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        *,
        max_chars_per_line: int | None = None,
        width_per_char_pixels: int | None = None,
        wrap_width_pixels: int | None = None,
        font_path: str | None = None,
        font_size: int | None = None,
    ):
        super().__init__(run_id, run_dir)
        from src.utils.config import Config
        config = Config.load()
        video_cfg = config.steps.video
        subtitle_cfg = config.steps.subtitle
        style_cfg = video_cfg.subtitles

        margin_l = int(style_cfg.margin_l or 0)
        margin_r = int(style_cfg.margin_r or 0)

        self.font_path = Path(font_path or style_cfg.font_path) if (font_path or style_cfg.font_path) else None
        self.font_size = font_size or style_cfg.font_size or 24

        overlay_l, overlay_r = self._overlay_guard(video_cfg.effects, video_cfg.resolution)
        margin_l = max(margin_l, overlay_l)
        margin_r = max(margin_r, overlay_r)

        safe_width = self.safe_pixel_width(video_cfg.resolution, margin_l, margin_r)
        target_width = max(int(safe_width * 0.8), 1)

        char_pixels = int(width_per_char_pixels or subtitle_cfg.width_per_char_pixels)
        char_pixels = max(char_pixels // 2, 1)

        if wrap_width_pixels is None:
            wrap_width_pixels = target_width

        if max_chars_per_line is None:
            estimated = target_width // char_pixels if char_pixels else subtitle_cfg.max_visual_width * 2
            limit = subtitle_cfg.max_visual_width * 2
            max_chars_per_line = max(subtitle_cfg.min_visual_width, min(limit, estimated))

        self.max_chars_per_line = max_chars_per_line
        self.width_per_char_pixels = char_pixels
        self.wrap_width_pixels = wrap_width_pixels
        self._font: ImageFont.ImageFont | None = None

    def execute(self, inputs: Dict[str, Path]) -> Path:
        validate_input_files(inputs, "generate_script", "synthesize_audio")
        script = load_script(Path(inputs["generate_script"]))
        audio_duration = get_audio_duration(Path(inputs["synthesize_audio"]))
        timestamps = self._calculate_timestamps(script, audio_duration)
        srt_content = self._generate_srt(timestamps)
        return write_text(self.get_output_path(), srt_content)

    def _calculate_timestamps(self, script, audio_duration: float) -> list[Dict]:
        total_chars = sum(len(seg.text) for seg in script.segments)
        if total_chars == 0:
            return []

        segments = script.segments
        gap = 0.0
        if len(segments) > 1:
            gap = min(0.2, audio_duration * 0.02)
            available = audio_duration - gap * (len(segments) - 1)
            if available <= 0:
                gap = 0.0
                available = audio_duration
        else:
            available = audio_duration

        timestamps = []
        current_time = 0.0
        for i, seg in enumerate(segments):
            char_ratio = len(seg.text) / total_chars
            duration = available * char_ratio if available > 0 else 0.0
            end_time = current_time + duration
            if i == len(segments) - 1:
                end_time = audio_duration
            timestamps.append({"start": current_time, "end": end_time, "text": seg.text})
            current_time = end_time + (gap if i < len(segments) - 1 else 0)
        return timestamps

    def _generate_srt(self, timestamps: list[Dict]) -> str:
        lines: List[str] = []
        for i, ts in enumerate(timestamps, start=1):
            lines.append(f"{i}")
            lines.append(f"{self._format_timestamp(ts['start'])} --> {self._format_timestamp(ts['end'])}")
            wrapped = self._wrap_text(ts["text"])
            lines.extend(wrapped)
            lines.append("")
        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _wrap_text(self, text: str) -> List[str]:
        limit = max(self.max_chars_per_line, 1)
        wrapped: List[str] = []
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                wrapped.append("")
                continue
            start = 0
            while start < len(line):
                wrapped.append(line[start : start + limit])
                start += limit
        return wrapped or [""]

    def _text_width(self, text: str) -> int:
        return len(text) * self.width_per_char_pixels

    def _load_font(self) -> ImageFont.ImageFont | None:
        if not self.font_path or not self.font_path.exists():
            return None
        if self._font is None:
            self._font = ImageFont.truetype(str(self.font_path), self.font_size or 24)
        return self._font

    @staticmethod
    def safe_pixel_width(resolution: str, margin_l: int | None, margin_r: int | None) -> int:
        width = int(resolution.lower().split("x", 1)[0].strip())
        return max(width - int(margin_l or 0) - int(margin_r or 0), 0)

    def _overlay_guard(self, effects, resolution: str) -> tuple[int, int]:
        width, height = map(int, resolution.split("x"))
        margin_l = 0
        margin_r = 0
        for effect in effects:
            if getattr(effect, "type", None) != "overlay" or not getattr(effect, "enabled", False):
                continue
            image_path = getattr(effect, "image_path", None)
            if not image_path:
                continue
            path = Path(str(image_path))
            if not path.exists():
                continue
            with Image.open(path) as img:
                orig_w, orig_h = img.size
            overlay_w = orig_w
            overlay_h = orig_h
            height_ratio = getattr(effect, "height_ratio", None)
            width_ratio = getattr(effect, "width_ratio", None)
            height_abs = getattr(effect, "height", None)
            width_abs = getattr(effect, "width", None)
            if height_ratio:
                overlay_h = int(height * float(height_ratio))
                overlay_w = int(orig_w * overlay_h / orig_h)
            elif width_ratio:
                overlay_w = int(width * float(width_ratio))
                overlay_h = int(orig_h * overlay_w / orig_w)
            elif height_abs:
                overlay_h = int(height_abs)
                overlay_w = int(orig_w * overlay_h / orig_h)
            elif width_abs:
                overlay_w = int(width_abs)
                overlay_h = int(orig_h * overlay_w / orig_w)
            anchor = getattr(effect, "anchor", "") or ""
            offset = getattr(effect, "offset", None)
            if hasattr(offset, "model_dump"):
                offset = offset.model_dump()
            offset = offset or {}
            padding = 20
            if "left" in anchor:
                margin_l = max(margin_l, int(offset.get("left") or 0) + overlay_w + padding)
            elif "right" in anchor:
                margin_r = max(margin_r, int(offset.get("right") or 0) + overlay_w + padding)
        return margin_l, margin_r
