from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict

import ffmpeg
from pydub import AudioSegment

from src.core.step import Step
from src.providers.video_effects import VideoEffectContext, VideoEffectPipeline


class VideoRenderer(Step):
    name = "render_video"
    output_filename = "video.mp4"

    def __init__(self, run_id: str, run_dir: Path, video_config: Dict | None = None):
        super().__init__(run_id, run_dir)
        self.video_config = video_config or {}
        self.resolution = self.video_config.get("resolution", "1920x1080")
        self.fps = self.video_config.get("fps", 25)
        self.codec = self.video_config.get("codec", "libx264")
        self.preset = self.video_config.get("preset", "medium")
        self.crf = self.video_config.get("crf", 23)
        self.effect_pipeline = VideoEffectPipeline.from_config(self.video_config.get("effects"))

    def execute(self, inputs: Dict[str, Path]) -> Path:
        audio_path = Path(inputs["synthesize_audio"])
        subtitle_path = Path(inputs["prepare_subtitles"])
        if not audio_path.exists() or not subtitle_path.exists():
            raise ValueError("Audio or subtitle file missing")

        audio_duration = self._get_audio_duration(audio_path)
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        width, height = map(int, self.resolution.split("x"))

        video_stream = ffmpeg.input(
            f"color=c=0x193d5a:size={width}x{height}:duration={audio_duration}:rate={self.fps}", f="lavfi"
        )

        effect_context = VideoEffectContext(
            duration_seconds=audio_duration,
            fps=self.fps,
            resolution=(width, height),
        )
        video_stream = self.effect_pipeline.apply(video_stream, effect_context)

        subtitle_path_str = str(subtitle_path).replace("\\", "/").replace(":", "\\:")
        video_stream = video_stream.filter(
            "subtitles",
            subtitle_path_str,
            force_style=(
                "FontName=Noto Sans CJK JP,FontSize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2"
            ),
        )

        audio_stream = ffmpeg.input(str(audio_path))

        output = ffmpeg.output(
            video_stream, audio_stream, str(output_path), vcodec=self.codec, preset=self.preset, crf=self.crf
        ).overwrite_output()

        ffmpeg.run(
            output,
            cmd=self._resolve_ffmpeg_binary(),
            capture_stdout=True,
            capture_stderr=True,
        )

        return output_path

    def _get_audio_duration(self, audio_path: Path) -> float:
        audio = AudioSegment.from_wav(audio_path)
        return len(audio) / 1000.0

    def _resolve_ffmpeg_binary(self) -> str:
        binary = shutil.which("ffmpeg")
        if not binary:
            raise FileNotFoundError("FFmpeg executable not found in PATH")
        return binary
