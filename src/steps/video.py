from __future__ import annotations

from pathlib import Path
from typing import Dict

import ffmpeg

from src.core.io_utils import validate_input_files
from src.core.media_utils import find_ffmpeg_binary, get_audio_duration, sanitize_path_for_ffmpeg
from src.core.step import Step
from src.providers.video_effects import VideoEffectContext, VideoEffectPipeline


class VideoRenderer(Step):
    name = "render_video"
    output_filename = "video.mp4"

    def __init__(self, run_id: str, run_dir: Path, video_config: Dict | None = None):
        super().__init__(run_id, run_dir)
        cfg = video_config or {}
        self.resolution = cfg.get("resolution", "1920x1080")
        self.fps = cfg.get("fps", 25)
        self.codec = cfg.get("codec", "libx264")
        self.preset = cfg.get("preset", "medium")
        self.crf = cfg.get("crf", 23)
        self.effect_pipeline = VideoEffectPipeline.from_config(cfg.get("effects"))
        subtitles_cfg = cfg.get("subtitles") or {}
        self.subtitle_force_style = self._build_subtitle_style(subtitles_cfg)
        self.subtitle_fonts_dir = self._resolve_fonts_dir(subtitles_cfg)

    def execute(self, inputs: Dict[str, Path]) -> Path:
        validate_input_files(inputs, "synthesize_audio", "prepare_subtitles")
        audio_path = Path(inputs["synthesize_audio"])
        subtitle_path = Path(inputs["prepare_subtitles"])
        audio_duration = get_audio_duration(audio_path)
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        width, height = map(int, self.resolution.split("x"))
        video_stream = ffmpeg.input(
            f"color=c=0x193d5a:size={width}x{height}:duration={audio_duration}:rate={self.fps}", f="lavfi"
        )

        effect_ctx = VideoEffectContext(duration_seconds=audio_duration, fps=self.fps, resolution=(width, height))
        video_stream = self.effect_pipeline.apply(video_stream, effect_ctx)

        subtitle_kwargs: Dict[str, str] = {}
        if self.subtitle_force_style:
            subtitle_kwargs["force_style"] = self.subtitle_force_style
        if self.subtitle_fonts_dir:
            subtitle_kwargs["fontsdir"] = self.subtitle_fonts_dir
        video_stream = video_stream.filter("subtitles", sanitize_path_for_ffmpeg(subtitle_path), **subtitle_kwargs)

        audio_stream = ffmpeg.input(str(audio_path))
        output = ffmpeg.output(
            video_stream, audio_stream, str(output_path), vcodec=self.codec, preset=self.preset, crf=self.crf
        ).overwrite_output()
        ffmpeg.run(output, cmd=find_ffmpeg_binary(), capture_stdout=True, capture_stderr=True)
        return output_path

    def _build_subtitle_style(self, config: Dict) -> str:
        font_name = str(config.get("font_name") or "").strip()
        if not font_name and (font_path := config.get("font_path")):
            font_name = Path(str(font_path)).stem.replace("_", " ")
        if not font_name:
            font_name = "Noto Sans CJK JP"

        parts = [
            f"FontName={font_name}",
            f"FontSize={int(config.get('font_size', 24))}",
            f"PrimaryColour={config.get('primary_colour', '&HFFFFFF&')}",
            f"OutlineColour={config.get('outline_colour', '&H000000&')}",
            f"Outline={int(config.get('outline', 2))}",
        ]
        for key in ("Shadow", "Bold", "Italic", "Alignment"):
            if (val := config.get(key.lower())) is not None:
                parts.append(f"{key}={val}")
        return ",".join(parts)

    def _resolve_fonts_dir(self, config: Dict) -> str | None:
        if not (font_path := config.get("font_path")):
            return None
        path = Path(str(font_path))
        return sanitize_path_for_ffmpeg(path.resolve().parent) if path.exists() else None
