from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict

from src.core.media_utils import resolve_video_input
from src.core.step import Step
from src.providers.twitter import TwitterClient


class TwitterPoster(Step):
    name = "post_twitter"
    output_filename = "tweet.json"
    is_required = False

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        twitter_config: dict | None = None,
        client: TwitterClient | None = None,
        clip_duration: int = 60,
        start_offset_seconds: float = 0.0,
        outro_path: str | None = None,
        encoder_options: Dict[str, str] | None = None,
        encoder_global_args: list[str] | None = None,
        codec: str | None = None,
        preset: str | None = None,
        crf: int | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: int | None = None,
        sample_rate: int | None = None,
    ) -> None:
        super().__init__(run_id, run_dir)
        self.clip_duration = clip_duration
        self.start_offset = start_offset_seconds
        dry_run = False
        if twitter_config:
            self.clip_duration = twitter_config.get("clip_duration_seconds", self.clip_duration)
            self.start_offset = twitter_config.get("start_offset_seconds", self.start_offset)
            dry_run = twitter_config.get("dry_run", False)
        if client:
            self.client = client
        elif twitter_config:
            self.client = TwitterClient.from_env(dry_run=dry_run)
        else:
            raise ValueError("Either twitter_config or client must be provided")
        self.outro_path = Path(outro_path) if outro_path else None
        options = {
            str(key): str(value)
            for key, value in (encoder_options or {}).items()
            if value is not None
        }
        if codec and "vcodec" not in options:
            options["vcodec"] = str(codec)
        if preset and "preset" not in options:
            options["preset"] = str(preset)
        if crf is not None and "crf" not in options:
            options["crf"] = str(crf)
        if "vcodec" not in options:
            options["vcodec"] = "libx264"
        if "preset" not in options:
            options["preset"] = "medium"
        if "acodec" not in options:
            options["acodec"] = "aac"
        self.encoder_options = options
        self.encoder_global_args = [str(arg) for arg in encoder_global_args or []]
        self.width = width
        self.height = height
        self.fps = fps
        self.sample_rate = sample_rate

    def execute(self, inputs: Dict[str, Path]) -> Path:
        base_video = inputs.get("concat_intro_outro")
        if base_video and Path(base_video).exists():
            video_path = Path(base_video)
        else:
            video_path = resolve_video_input(inputs)
        metadata_path = Path(inputs["analyze_metadata"])
        clip_path = self.run_dir / self.run_id / "twitter_clip.mp4"
        clip_path.parent.mkdir(parents=True, exist_ok=True)
        global_args = self._ffmpeg_global_args()
        clip_cmd = ["ffmpeg", "-y", *global_args]
        if self.start_offset > 0:
            clip_cmd.extend(["-ss", str(self.start_offset)])
        clip_cmd.extend(["-i", str(video_path), "-t", str(self.clip_duration)])
        needs_encode = self.start_offset > 0 and self.encoder_options and all(
            value is not None for value in (self.width, self.height, self.fps, self.sample_rate)
        )
        if needs_encode:
            filters = [
                f"scale={self.width}:{self.height}",
                "setsar=1",
                f"fps={self.fps}",
            ]
            clip_cmd.extend(
                [
                    "-vf",
                    ",".join(filters),
                ]
            )
            clip_cmd.extend(self._encoder_cli_args())
            clip_cmd.extend(["-ar", str(self.sample_rate)])
        else:
            clip_cmd.extend(["-c", "copy"])
        clip_cmd.append(str(clip_path))
        subprocess.run(clip_cmd, check=True)
        if self.outro_path:
            if not self.outro_path.exists():
                raise FileNotFoundError(str(self.outro_path))
            final_path = clip_path.with_name("twitter_clip_with_outro.mp4")
            filter_expr = (
                f"[0:v]scale={self.width}:{self.height},setsar=1,fps={self.fps},setpts=PTS-STARTPTS[v0];"
                f"[0:a]aresample={self.sample_rate},asetpts=PTS-STARTPTS[a0];"
                f"[1:v]scale={self.width}:{self.height},setsar=1,fps={self.fps},setpts=PTS-STARTPTS[v1];"
                f"[1:a]aresample={self.sample_rate},asetpts=PTS-STARTPTS[a1];"
                "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
            )
            concat_cmd = [
                "ffmpeg",
                "-y",
                *global_args,
                "-i",
                str(clip_path),
                "-i",
                str(self.outro_path),
                "-filter_complex",
                filter_expr,
                "-map",
                "[v]",
                "-map",
                "[a]",
            ]
            concat_cmd.extend(self._encoder_cli_args())
            if self.sample_rate is not None:
                concat_cmd.extend(["-ar", str(self.sample_rate)])
            concat_cmd.append(str(final_path))
            subprocess.run(concat_cmd, check=True)
            clip_path.unlink()
            final_path.rename(clip_path)
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        tags = payload.get("tags", [])[:5]
        suffix = " ".join(tags)
        text = payload.get("title", "")
        if suffix:
            text = f"{text}\n{suffix}"
        result = self.client.post(text, clip_path)
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    def _encoder_cli_args(self) -> list[str]:
        args: list[str] = []
        for key, value in self.encoder_options.items():
            args.extend([self._encoder_flag(key), str(value)])
        return args

    def _encoder_flag(self, key: str) -> str:
        if key == "vcodec":
            return "-c:v"
        if key == "acodec":
            return "-c:a"
        return f"-{key}"

    def _ffmpeg_global_args(self) -> list[str]:
        args: list[str] = []
        skip = False
        for arg in self.encoder_global_args:
            if skip:
                skip = False
                continue
            if arg in {"-hwaccel", "-hwaccel_output_format"}:
                skip = True
                continue
            args.append(arg)
        return args


if __name__ == "__main__":
    from pathlib import Path
    from dotenv import load_dotenv
    from src.providers.twitter import TwitterClient

    # Load environment variables from .env file
    env_path = Path(__file__).resolve().parents[2] / "config" / ".env"
    load_dotenv(dotenv_path=env_path)

    RUN_ID = "20251015_193631"
    RUN_DIR = Path("runs")
    CLIP_DURATION = 60
    DRY_RUN = False  # Set to True to prevent actual posting

    # Initialize the client directly from environment variables
    client = TwitterClient.from_env(dry_run=DRY_RUN)

    poster = TwitterPoster(
        run_id=RUN_ID,
        run_dir=RUN_DIR,
        client=client,
        clip_duration=CLIP_DURATION,
    )

    inputs = {
        "render_video": RUN_DIR / RUN_ID / "video.mp4",
        "analyze_metadata": RUN_DIR / RUN_ID / "metadata.json",
    }

    output_path = poster.execute(inputs)
    print(f"Output: {output_path}")
