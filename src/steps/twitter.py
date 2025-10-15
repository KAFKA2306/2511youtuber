from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict

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
        client: TwitterClient,
        clip_duration: int = 60,
        thumbnail_path: Path | str | None = None,
    ) -> None:
        super().__init__(run_id, run_dir)
        self.clip_duration = clip_duration
        self.thumbnail_path = Path(thumbnail_path) if thumbnail_path else None
        self.client = client

    def execute(self, inputs: Dict[str, Path]) -> Path:
        video_path = Path(inputs["render_video"])
        metadata_path = Path(inputs["analyze_metadata"])
        clip_path = self.run_dir / self.run_id / "twitter_clip.mp4"
        clip_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-t",
                str(self.clip_duration),
                "-c",
                "copy",
                str(clip_path),
            ],
            check=True,
        )
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        tags = payload.get("tags", [])[:5]
        suffix = " ".join(tags)
        text = payload.get("title", "")
        if suffix:
            text = f"{text}\n{suffix}"
        result = self.client.post(text, clip_path, self.thumbnail_path)
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path


if __name__ == "__main__":
    from pathlib import Path
    from dotenv import load_dotenv
    from src.providers.twitter import TwitterClient

    # Load environment variables from .env file
    env_path = Path(__file__).resolve().parents[2] / "config" / ".env"
    load_dotenv(dotenv_path=env_path)

    RUN_ID = "20251015_193631"
    RUN_DIR = Path("runs")
    THUMBNAIL_PATH = RUN_DIR / RUN_ID / "thumbnail.png"
    CLIP_DURATION = 60
    DRY_RUN = False  # Set to True to prevent actual posting

    # Initialize the client directly from environment variables
    client = TwitterClient.from_env(dry_run=DRY_RUN)

    poster = TwitterPoster(
        run_id=RUN_ID,
        run_dir=RUN_DIR,
        client=client,
        clip_duration=CLIP_DURATION,
        thumbnail_path=THUMBNAIL_PATH,
    )

    inputs = {
        "render_video": RUN_DIR / RUN_ID / "video.mp4",
        "analyze_metadata": RUN_DIR / RUN_ID / "metadata.json",
    }

    output_path = poster.execute(inputs)
    print(f"Output: {output_path}")