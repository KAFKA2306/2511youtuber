from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Tuple

import ffmpeg

from src.core.io_utils import validate_input_files
from src.core.media_utils import apply_thumbnail_overlay, find_ffmpeg_binary
from src.core.step import Step


class IntroOutroConcatenator(Step):
    name = "concat_intro_outro"
    output_filename = "video_intro_outro.mp4"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        *,
        intro_path: str | None,
        outro_path: str | None,
        codec: str,
        preset: str,
        crf: int,
        thumbnail_overlay: Dict | None = None,
        thumbnail_clip: Dict | None = None,
    ) -> None:
        super().__init__(run_id, run_dir)
        self.intro_path = Path(intro_path) if intro_path else None
        self.outro_path = Path(outro_path) if outro_path else None
        self.codec = codec
        self.preset = preset
        self.crf = crf
        overlay_cfg = thumbnail_overlay or {}
        self.thumbnail_overlay_enabled = bool(overlay_cfg.get("enabled", False))
        self.thumbnail_overlay_duration = float(overlay_cfg.get("duration_seconds", 0))
        self.thumbnail_overlay_source = str(overlay_cfg.get("source_key", "generate_thumbnail"))
        clip_cfg = thumbnail_clip or {}
        self.thumbnail_clip_enabled = bool(clip_cfg.get("enabled", False))
        self.thumbnail_clip_duration = float(clip_cfg.get("duration_seconds", 0))
        self.thumbnail_clip_source = str(clip_cfg.get("source_key", "generate_thumbnail"))

    def execute(self, inputs: Dict[str, Path]) -> Path:
        validate_input_files(inputs, "render_video")
        base_path = Path(inputs["render_video"])
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        width, height, fps, sample_rate = self._profile(base_path)
        clip_path = self._ensure_thumbnail_clip(inputs, width, height, fps, sample_rate)
        segments = self._segments(base_path, clip_path)
        if len(segments) == 1:
            if base_path == output_path:
                return base_path
            shutil.copyfile(base_path, output_path)
            return output_path
        video_streams, audio_streams = self._aligned_streams(segments, width, height, fps, sample_rate)
        video_concat = ffmpeg.concat(*video_streams, v=1, a=0).node
        audio_concat = ffmpeg.concat(*audio_streams, v=0, a=1).node
        video_output = video_concat[0]
        if self.thumbnail_overlay_enabled and self.thumbnail_overlay_duration > 0:
            thumbnail_input = inputs.get(self.thumbnail_overlay_source)
            if thumbnail_input:
                thumbnail_path = Path(thumbnail_input)
                video_output = apply_thumbnail_overlay(
                    video_output,
                    thumbnail_path,
                    duration=self.thumbnail_overlay_duration,
                    width=width,
                    height=height,
                    fps=fps,
                )
        output = ffmpeg.output(
            video_output,
            audio_concat[0],
            str(output_path),
            vcodec=self.codec,
            preset=self.preset,
            crf=self.crf,
            acodec="aac",
        ).overwrite_output()
        ffmpeg.run(output, cmd=find_ffmpeg_binary(), capture_stdout=True, capture_stderr=True)
        return output_path

    def _ensure_thumbnail_clip(
        self,
        inputs: Dict[str, Path],
        width: int,
        height: int,
        fps: int | None,
        sample_rate: int,
    ) -> Path | None:
        if not self.intro_path or not self.thumbnail_clip_enabled or self.thumbnail_clip_duration <= 0:
            return None
        source = inputs.get(self.thumbnail_clip_source)
        if not source:
            return None
        thumbnail_path = Path(source)
        if not thumbnail_path.exists():
            return None
        clip_path = self.get_output_path().with_name("thumbnail_clip.mp4")
        if clip_path.exists():
            return clip_path
        clip_path.parent.mkdir(parents=True, exist_ok=True)
        frame_rate = fps or 25
        video = (
            ffmpeg.input(str(thumbnail_path), loop=1, framerate=frame_rate)
            .filter("scale", width, height)
            .filter("setsar", "1")
            .filter("trim", duration=self.thumbnail_clip_duration)
            .filter("setpts", "PTS-STARTPTS")
        )
        audio = (
            ffmpeg.input(f"anullsrc=channel_layout=stereo:sample_rate={sample_rate}", f="lavfi")
            .filter("atrim", duration=self.thumbnail_clip_duration)
            .filter("asetpts", "PTS-STARTPTS")
        )
        output = (
            ffmpeg.output(
                video,
                audio,
                str(clip_path),
                vcodec=self.codec,
                preset=self.preset,
                crf=self.crf,
                acodec="aac",
            ).overwrite_output()
        )
        ffmpeg.run(output, cmd=find_ffmpeg_binary(), capture_stdout=True, capture_stderr=True)
        return clip_path

    def _segments(self, base_path: Path, clip_path: Path | None) -> list[Path]:
        paths: list[Path] = []
        if clip_path:
            paths.append(self._require(clip_path))
        if self.intro_path:
            paths.append(self._require(self.intro_path))
        paths.append(self._require(base_path))
        if self.outro_path:
            paths.append(self._require(self.outro_path))
        return paths

    def _require(self, path: Path) -> Path:
        if not path.exists():
            raise FileNotFoundError(str(path))
        return path.resolve()

    def _profile(self, path: Path) -> Tuple[int, int, int | None, int]:
        data = ffmpeg.probe(str(path))
        video_stream = next(stream for stream in data.get("streams", []) if stream.get("codec_type") == "video")
        width = int(video_stream.get("width"))
        height = int(video_stream.get("height"))
        rate_value = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or ""
        fps = self._frame_rate(rate_value)
        audio_stream = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"), None)
        sample_rate = int(audio_stream.get("sample_rate")) if audio_stream and audio_stream.get("sample_rate") else 48000
        return width, height, fps, sample_rate

    def _aligned_streams(
        self,
        segments: list[Path],
        width: int,
        height: int,
        fps: int | None,
        sample_rate: int,
    ) -> Tuple[list, list]:
        video_streams = []
        audio_streams = []
        for path in segments:
            stream = ffmpeg.input(str(path))
            video = stream.video.filter("scale", width, height).filter("setsar", "1")
            if fps:
                video = video.filter("fps", fps=fps)
            video = video.filter("setpts", "PTS-STARTPTS")
            audio = stream.audio.filter("aresample", sample_rate).filter("asetpts", "PTS-STARTPTS")
            video_streams.append(video)
            audio_streams.append(audio)
        return video_streams, audio_streams

    def _frame_rate(self, value: str) -> int | None:
        if not value or value == "0/0":
            return None
        parts = value.split("/")
        if len(parts) != 2:
            return None
        numerator, denominator = parts
        if denominator == "0":
            return None
        return int(round(int(numerator) / int(denominator)))
