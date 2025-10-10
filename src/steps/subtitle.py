import json
import textwrap
from pathlib import Path
from typing import Dict, List

from pydub import AudioSegment

from src.models import Script
from src.steps.base import Step


class SubtitleFormatter(Step):
    name = "prepare_subtitles"
    output_filename = "subtitles.srt"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        *,
        max_chars_per_line: int = 24,
    ):
        super().__init__(run_id, run_dir)
        self.max_chars_per_line = max(8, max_chars_per_line)

    def execute(self, inputs: Dict[str, Path]) -> Path:
        script_path = inputs.get("generate_script")
        audio_path = inputs.get("synthesize_audio")

        if not script_path or not Path(script_path).exists():
            raise ValueError("Script file not found")
        if not audio_path or not Path(audio_path).exists():
            raise ValueError("Audio file not found")

        script = self._load_script(Path(script_path))
        audio_duration = self._get_audio_duration(Path(audio_path))

        self.logger.info(
            f"Generating subtitles",
            segments=len(script.segments),
            audio_duration_seconds=audio_duration
        )

        timestamps = self._calculate_timestamps(script, audio_duration)
        srt_content = self._generate_srt(timestamps)

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        self.logger.info(f"Subtitles generated", output_path=str(output_path))
        return output_path

    def _load_script(self, script_path: Path) -> Script:
        with open(script_path, encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)

    def _get_audio_duration(self, audio_path: Path) -> float:
        audio = AudioSegment.from_wav(audio_path)
        return len(audio) / 1000.0

    def _calculate_timestamps(self, script: Script, audio_duration: float) -> list[Dict]:
        total_chars = sum(len(seg.text) for seg in script.segments)
        if total_chars == 0:
            return []

        segments = script.segments
        gap = 0.0
        if len(segments) > 1:
            # Reserve a small buffer between segments so timestamps don't overlap
            gap = min(0.2, audio_duration * 0.02)
            available_duration = audio_duration - gap * (len(segments) - 1)
            if available_duration <= 0:
                gap = 0.0
                available_duration = audio_duration
        else:
            available_duration = audio_duration

        current_time = 0.0
        timestamps = []

        for index, segment in enumerate(segments):
            char_ratio = len(segment.text) / total_chars
            duration = available_duration * char_ratio if available_duration > 0 else 0.0

            end_time = current_time + duration
            if index == len(segments) - 1:
                end_time = audio_duration

            timestamps.append({
                "start": current_time,
                "end": end_time,
                "text": segment.text
            })

            current_time = end_time
            if index < len(segments) - 1:
                current_time += gap

        return timestamps

    def _generate_srt(self, timestamps: list[Dict]) -> str:
        srt_lines: List[str] = []

        for i, ts in enumerate(timestamps, start=1):
            start_time = self._format_timestamp(ts["start"])
            end_time = self._format_timestamp(ts["end"])

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.extend(self._wrap_text(ts["text"]))
            srt_lines.append("")

        return "\n".join(srt_lines)

    def _format_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _wrap_text(self, text: str) -> List[str]:
        wrapped_lines: List[str] = []

        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                wrapped_lines.append("")
                continue

            segments = textwrap.wrap(
                line,
                width=self.max_chars_per_line,
                break_long_words=True,
                break_on_hyphens=False,
            )
            if not segments:
                wrapped_lines.append("")
                continue
            wrapped_lines.extend(segments)

        return wrapped_lines or [""]
