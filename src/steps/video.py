from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict

import ffmpeg
from pydub import AudioSegment

try:
    import imageio_ffmpeg  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    imageio_ffmpeg = None

from src.providers.video_effects import VideoEffectContext, VideoEffectPipeline
from src.steps.base import Step


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
        audio_path = inputs.get("synthesize_audio")
        subtitle_path = inputs.get("prepare_subtitles")

        if not audio_path or not Path(audio_path).exists():
            raise ValueError("Audio file not found")
        if not subtitle_path or not Path(subtitle_path).exists():
            raise ValueError("Subtitle file not found")

        audio_duration = self._get_audio_duration(Path(audio_path))

        self.logger.info("Rendering video", audio_duration=audio_duration, resolution=self.resolution, fps=self.fps)

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

        try:
            ffmpeg.run(
                output,
                cmd=self._resolve_ffmpeg_binary(),
                capture_stdout=True,
                capture_stderr=True,
            )
        except ffmpeg.Error as e:
            self.logger.error(
                "FFmpeg failed",
                stderr=e.stderr.decode() if e.stderr else "",
                stdout=e.stdout.decode() if e.stdout else "",
            )
            raise

        self.logger.info("Video rendered successfully", output_path=str(output_path))
        return output_path

    def _get_audio_duration(self, audio_path: Path) -> float:
        audio = AudioSegment.from_wav(audio_path)
        return len(audio) / 1000.0

    def _resolve_ffmpeg_binary(self) -> str | None:
        """Return the ffmpeg binary path, using bundled fallbacks when available."""

        system_binary = shutil.which("ffmpeg")
        if system_binary:
            return system_binary

        if imageio_ffmpeg is not None:  # pragma: no branch - simple guard
            try:
                return imageio_ffmpeg.get_ffmpeg_exe()
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.warning("Failed to load bundled ffmpeg", error=str(exc))

        raise FileNotFoundError(
            "FFmpeg executable not found. Install ffmpeg or add it to PATH, or ensure imageio-ffmpeg is available."
        )
