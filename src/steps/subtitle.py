import json
from pathlib import Path
from typing import Dict
from pydub import AudioSegment
from src.steps.base import Step
from src.models import Script


class SubtitleFormatter(Step):
    name = "prepare_subtitles"
    output_filename = "subtitles.srt"

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

        current_time = 0.0
        timestamps = []

        for segment in script.segments:
            char_ratio = len(segment.text) / total_chars
            duration = audio_duration * char_ratio

            timestamps.append({
                "start": current_time,
                "end": current_time + duration,
                "text": segment.text
            })
            current_time += duration

        return timestamps

    def _generate_srt(self, timestamps: list[Dict]) -> str:
        srt_lines = []

        for i, ts in enumerate(timestamps, start=1):
            start_time = self._format_timestamp(ts["start"])
            end_time = self._format_timestamp(ts["end"])

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(ts["text"])
            srt_lines.append("")

        return "\n".join(srt_lines)

    def _format_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
