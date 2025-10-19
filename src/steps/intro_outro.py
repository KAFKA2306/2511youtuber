from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Tuple

import ffmpeg

from src.core.io_utils import validate_input_files
from src.core.media_utils import find_ffmpeg_binary
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
    ) -> None:
        super().__init__(run_id, run_dir)
        self.intro_path = Path(intro_path) if intro_path else None
        self.outro_path = Path(outro_path) if outro_path else None
        self.codec = codec
        self.preset = preset
        self.crf = crf

    def execute(self, inputs: Dict[str, Path]) -> Path:
        validate_input_files(inputs, "render_video")
        base_path = Path(inputs["render_video"])
        segments = self._segments(base_path)
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if len(segments) == 1:
            if base_path == output_path:
                return base_path
            shutil.copyfile(base_path, output_path)
            return output_path
        width, height, fps, sample_rate = self._profile(base_path)
        video_streams, audio_streams = self._aligned_streams(segments, width, height, fps, sample_rate)
        video_concat = ffmpeg.concat(*video_streams, v=1, a=0).node
        audio_concat = ffmpeg.concat(*audio_streams, v=0, a=1).node
        output = ffmpeg.output(
            video_concat[0],
            audio_concat[0],
            str(output_path),
            vcodec=self.codec,
            preset=self.preset,
            crf=self.crf,
            acodec="aac",
        ).overwrite_output()
        ffmpeg.run(output, cmd=find_ffmpeg_binary(), capture_stdout=True, capture_stderr=True)
        return output_path

    def _segments(self, base_path: Path) -> list[Path]:
        paths: list[Path] = []
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
