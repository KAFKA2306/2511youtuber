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
        twitter_config: Dict | None = None,
    ) -> None:
        super().__init__(run_id, run_dir)
        twitter_config = twitter_config or {}
        self.clip_duration = int(twitter_config.get("clip_duration_seconds", 60))
        self.thumbnail_path = Path(twitter_config.get("thumbnail_path", "runs/20251015_183513/thumbnail.png"))
        self.client = TwitterClient.from_config(twitter_config, dry_run=bool(twitter_config.get("dry_run", True)))

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
