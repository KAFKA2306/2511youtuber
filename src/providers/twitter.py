from __future__ import annotations

from pathlib import Path
from typing import Dict

import tweepy

from src.utils.secrets import load_secret_values


class TwitterClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_secret: str,
        *,
        dry_run: bool = False,
    ) -> None:
        self.dry_run = dry_run
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        self.api = tweepy.API(auth)

    @staticmethod
    def _secret(config: Dict, key: str) -> str:
        name = config.get(key, "")
        values = load_secret_values(name)
        return values[0] if values else ""

    @classmethod
    def from_config(cls, config: Dict, *, dry_run: bool) -> "TwitterClient":
        return cls(
            cls._secret(config, "api_key"),
            cls._secret(config, "api_secret"),
            cls._secret(config, "access_token"),
            cls._secret(config, "access_secret"),
            dry_run=dry_run,
        )

    def post(self, text: str, video_path: Path, image_path: Path) -> Dict:
        if self.dry_run:
            return {
                "status": text,
                "video": str(video_path),
                "image": str(image_path),
            }
        video_media = self.api.media_upload(filename=str(video_path), media_category="tweet_video")
        image_media = self.api.media_upload(filename=str(image_path))
        tweet = self.api.update_status(status=text, media_ids=[video_media.media_id_string, image_media.media_id_string])
        return {
            "id": tweet.id_str,
            "text": tweet.text,
            "media_ids": [video_media.media_id_string, image_media.media_id_string],
        }
