from __future__ import annotations

import logging
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import tweepy

from src.utils.secrets import load_secret_values

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _first_secret_value(config: Dict, key: str) -> str:
    name = config.get(key, "")
    values = load_secret_values(name)
    return values[0] if values else ""


def _get_env_any(*names: str) -> Optional[str]:
    for n in names:
        if v := os.getenv(n):
            return v
    return None


def _is_video(path: Path) -> bool:
    mt, _ = mimetypes.guess_type(str(path))
    return (mt or "").startswith("video/")


@dataclass
class TwitterClient:
    api: Optional[tweepy.API]
    client: Optional[tweepy.Client]
    dry_run: bool = False

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_secret: str,
        *,
        dry_run: bool = False,
        wait_on_rate_limit: bool = True,
    ) -> None:
        self.dry_run = dry_run
        if dry_run:
            self.api = None
            self.client = None
            logger.info("TwitterClient initialized in DRY RUN mode.")
            return

        if not all([api_key, api_secret, access_token, access_secret]):
            raise RuntimeError("Twitter OAuth1.1a credentials are missing.")

        auth_v1 = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        self.api = tweepy.API(auth_v1, wait_on_rate_limit=wait_on_rate_limit)
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )

        me_v1 = self.api.verify_credentials()
        logger.info("Twitter API v1.1 authenticated as @%s", getattr(me_v1, "screen_name", "unknown"))
        me_v2 = self.client.get_me()
        logger.info("Twitter API v2 authenticated as @%s", getattr(me_v2.data, "username", "unknown"))

    @classmethod
    def from_config(cls, config: Dict, *, dry_run: bool) -> "TwitterClient":
        return cls(
            _first_secret_value(config, "api_key"),
            _first_secret_value(config, "api_secret"),
            _first_secret_value(config, "access_token"),
            _first_secret_value(config, "access_secret"),
            dry_run=dry_run,
        )

    @classmethod
    def from_env(cls, *, dry_run: Optional[bool] = None) -> "TwitterClient":
        if dry_run is None:
            dry_run = os.getenv("TWITTER_DRY_RUN", "0") == "1"
        if dry_run:
            return cls("", "", "", "", dry_run=True)
        return cls(
            _get_env_any("X_API_KEY", "TWITTER_API_KEY") or "",
            _get_env_any("X_API_SECRET", "TWITTER_API_SECRET") or "",
            _get_env_any("X_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN") or "",
            _get_env_any("X_ACCESS_SECRET", "TWITTER_ACCESS_TOKEN_SECRET") or "",
            dry_run=False,
        )

    def post(self, text: str, video_path: Path | str | None = None) -> Dict:
        if self.dry_run:
            logger.info("[DRY_RUN] tweet: %s", text)
            return {"status": text, "video": str(video_path) if video_path else None, "dry_run": True}

        media_ids = []
        if video_path:
            video_path = Path(video_path) if not isinstance(video_path, Path) else video_path
            if not video_path.exists():
                raise FileNotFoundError(f"Video not found: {video_path}")
            media_ids.append(self._upload_video(video_path))

        response = self.client.create_tweet(text=text, media_ids=media_ids if media_ids else None)
        tweet_data = response.data or {}
        return {"id": tweet_data.get("id"), "text": tweet_data.get("text"), "media_ids": media_ids}

    def _upload_video(self, path: Path) -> str:
        if not _is_video(path):
            logger.warning("Video mime-type unknown; attempting upload anyway: %s", path)
        media = self.api.media_upload(filename=str(path), media_category="tweet_video")
        return media.media_id_string
