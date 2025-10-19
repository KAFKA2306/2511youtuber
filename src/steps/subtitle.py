import re
import unicodedata
from pathlib import Path
from typing import Dict, List

from PIL import ImageFont

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
        max_chars_per_line: int,
        width_per_char_pixels: int,
        wrap_width_pixels: int | None = None,
        font_path: str | None = None,
        font_size: int | None = None,
    ):
        super().__init__(run_id, run_dir)
        self.max_chars_per_line = max_chars_per_line
        self.width_per_char_pixels = width_per_char_pixels
        self.wrap_width_pixels = wrap_width_pixels
        self.font_path = Path(font_path) if font_path else None
        self.font_size = font_size
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
            lines.extend(self._wrap_text(ts["text"]))
            lines.append("")
        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _wrap_text(self, text: str) -> List[str]:
        wrapped = []
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                wrapped.append("")
                continue
            wrapped.extend(self._wrap_visual_line(line, self.max_chars_per_line))
        return wrapped or [""]

    def _wrap_visual_line(self, line: str, limit: int) -> List[str]:
        if not line:
            return [""]
        sentences = re.split(r'(?<=。)', line)
        segments, current = [], ""
        for sentence in sentences:
            if not sentence:
                continue
            for chunk in self._split_by_width(sentence, limit):
                if not chunk:
                    continue
                tentative = current + chunk
                if current and self._exceeds_limits(tentative, limit):
                    segments.append(current)
                    current = chunk
                else:
                    current = tentative
        if current:
            segments.append(current)
        cleaned = [seg for seg in segments if seg]
        return cleaned or [""]

    def _split_by_width(self, text: str, limit: int) -> List[str]:
        if not text:
            return [""]
        if limit <= 0 and not self.wrap_width_pixels:
            return [text]
        chunks, current = [], ""
        for char in text:
            tentative = current + char
            if current and self._exceeds_limits(tentative, limit):
                chunks.append(current)
                current = char
            elif not current and self._exceeds_limits(tentative, limit):
                chunks.append(char)
                current = ""
            else:
                current = tentative
        if current:
            chunks.append(current)
        return chunks or [""]

    def _visual_width(self, text: str) -> int:
        return sum(2 if unicodedata.east_asian_width(c) in ("F", "W") else 1 for c in text)

    def _text_width(self, text: str) -> int:
        font = self._load_font()
        if font:
            if hasattr(font, "getlength"):
                return int(font.getlength(text))
            bbox = font.getbbox(text)
            return int(bbox[2] - bbox[0])
        return self._visual_width(text) * self.width_per_char_pixels

    def _load_font(self) -> ImageFont.ImageFont | None:
        if not self.font_path or not self.font_path.exists():
            return None
        if self._font is None:
            size = self.font_size or 24
            self._font = ImageFont.truetype(str(self.font_path), size)
        return self._font

    def _exceeds_limits(self, text: str, limit: int) -> bool:
        if limit > 0 and self._visual_width(text) > limit:
            return True
        if self.wrap_width_pixels and self._text_width(text) > self.wrap_width_pixels:
            return True
        return False

    @staticmethod
    def estimate_max_chars_per_line(
        resolution: str,
        width_per_char_pixels: int,
        min_visual_width: int,
        max_visual_width: int,
        margin_l: int | None = None,
        margin_r: int | None = None,
    ) -> int:
        safe = SubtitleFormatter.safe_pixel_width(resolution, margin_l, margin_r)
        base = int(max(safe, 0) / width_per_char_pixels) if width_per_char_pixels else min_visual_width
        return max(min_visual_width, min(max_visual_width, base))

    @staticmethod
    def safe_pixel_width(resolution: str, margin_l: int | None, margin_r: int | None) -> int:
        width = int(resolution.lower().split("x", 1)[0].strip())
        return max(width - int(margin_l or 0) - int(margin_r or 0), 0)
