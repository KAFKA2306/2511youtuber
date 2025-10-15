import unicodedata
from pathlib import Path
from typing import Dict, List

from src.core.io_utils import load_script, validate_input_files, write_text
from src.core.media_utils import get_audio_duration
from src.core.step import Step


class SubtitleFormatter(Step):
    name = "prepare_subtitles"
    output_filename = "subtitles.srt"

    def __init__(self, run_id: str, run_dir: Path, *, max_chars_per_line: int):
        super().__init__(run_id, run_dir)
        self.max_chars_per_line = max_chars_per_line

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
        segments, current, width = [], [], 0
        for char in line:
            char_w = 2 if unicodedata.east_asian_width(char) in ("F", "W") else 1
            if current and width + char_w > limit:
                segments.append("".join(current))
                current, width = [char], char_w
            else:
                current.append(char)
                width += char_w
        if current:
            segments.append("".join(current))
        return segments or [""]
