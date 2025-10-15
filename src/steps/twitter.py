from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict

from src.core.step import Step
from src.providers.twitter import TwitterClient


class TwitterPoster(Step):
    name = "post_twitter"
    output_filename = "twitter.json"
    is_required = False

    def __init__(self, run_id: str, run_dir: Path, twitter_config: Dict | None = None) -> None:
        super().__init__(run_id, run_dir)
        twitter_config = twitter_config or {}
        self.clip_duration = int(twitter_config.get("clip_duration_seconds", 60))
        self.chunk_size = int(twitter_config.get("chunk_size", 5_242_880))
        self.thumbnail_filename = twitter_config.get("thumbnail_filename", "thumbnail.png")
        self.client = TwitterClient(
            api_key_key=twitter_config.get("api_key_key", "TWITTER_API_KEY"),
            api_secret_key=twitter_config.get("api_secret_key", "TWITTER_API_SECRET"),
            access_token_key=twitter_config.get("access_token_key", "TWITTER_ACCESS_TOKEN"),
            access_secret_key=twitter_config.get("access_secret_key", "TWITTER_ACCESS_SECRET"),
        )

    def execute(self, inputs: Dict[str, Path]) -> Path:
        video_path = Path(inputs["render_video"])
        metadata_path = Path(inputs["analyze_metadata"])
        output_dir = self.run_dir / self.run_id
        clip_path = output_dir / "twitter_clip.mp4"
        clip_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-ss",
                "0",
                "-t",
                str(self.clip_duration),
                "-c",
                "copy",
                str(clip_path),
            ],
            check=True,
        )
        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)
        title = str(metadata.get("title", ""))
        tags = metadata.get("tags") or []
        tags_text = " ".join(tag for tag in tags[:5] if tag)
        text = title if not tags_text else f"{title} {tags_text}".strip()
        thumbnail_path = output_dir / self.thumbnail_filename
        if inputs.get("generate_thumbnail"):
            thumbnail_path = Path(inputs["generate_thumbnail"])
        result = self.client.post_video(
            text=text,
            video_path=clip_path,
            thumbnail_path=thumbnail_path if thumbnail_path.exists() else None,
            chunk_size=self.chunk_size,
        )
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return output_path
