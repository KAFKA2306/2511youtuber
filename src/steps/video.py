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
        subtitles_cfg = self.video_config.get("subtitles") or {}
        self.subtitle_force_style = self._build_subtitle_force_style(subtitles_cfg)
        self.subtitle_fonts_dir = self._resolve_subtitle_fonts_dir(subtitles_cfg)

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

        subtitle_path_str = self._sanitize_path_for_ffmpeg(subtitle_path)
        subtitle_filter_kwargs: Dict[str, str] = {}
        if self.subtitle_force_style:
            subtitle_filter_kwargs["force_style"] = self.subtitle_force_style
        if self.subtitle_fonts_dir:
            subtitle_filter_kwargs["fontsdir"] = self.subtitle_fonts_dir
        video_stream = video_stream.filter("subtitles", subtitle_path_str, **subtitle_filter_kwargs)

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

    def _build_subtitle_force_style(self, config: Dict) -> str:
        font_name = str(config.get("font_name") or "").strip()
        font_path_value = config.get("font_path")
        if not font_name and font_path_value:
            font_name = Path(str(font_path_value)).stem.replace("_", " ")
        if not font_name:
            font_name = "Noto Sans CJK JP"

        font_size = int(config.get("font_size", 24))
        primary_colour = str(config.get("primary_colour", "&HFFFFFF&"))
        outline_colour = str(config.get("outline_colour", "&H000000&"))
        outline = int(config.get("outline", 2))

        style_parts = [
            f"FontName={font_name}",
            f"FontSize={font_size}",
            f"PrimaryColour={primary_colour}",
            f"OutlineColour={outline_colour}",
            f"Outline={outline}",
        ]

        optional_fields = {
            "Shadow": config.get("shadow"),
            "Bold": config.get("bold"),
            "Italic": config.get("italic"),
            "Alignment": config.get("alignment"),
        }

        for key, value in optional_fields.items():
            if value is not None:
                style_parts.append(f"{key}={value}")

        return ",".join(style_parts)

    def _resolve_subtitle_fonts_dir(self, config: Dict) -> str | None:
        font_path_value = config.get("font_path")
        if not font_path_value:
            return None
        font_path = Path(str(font_path_value))
        if not font_path.exists():
            return None
        return self._sanitize_path_for_ffmpeg(font_path.resolve().parent)

    def _sanitize_path_for_ffmpeg(self, path: Path) -> str:
        return str(path).replace("\\", "/").replace(":", "\\:")
