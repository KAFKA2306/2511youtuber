from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import os
import time
import mimetypes
import logging

import tweepy

from src.utils.secrets import load_secret_values

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _first_secret_value(config: Dict, key: str) -> str:
    """
    config[key] に格納された “シークレット名” から最初の値を取り出す。
    値がなければ空文字を返す。
    """
    name = config.get(key, "")
    values = load_secret_values(name)
    return values[0] if values else ""


def _get_env_any(*names: str) -> Optional[str]:
    """候補名のうち最初に見つかった環境変数の値を返す。"""
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None


def _is_video(path: Path) -> bool:
    mt, _ = mimetypes.guess_type(str(path))
    return (mt or "").startswith("video/")


def _is_image(path: Path) -> bool:
    mt, _ = mimetypes.guess_type(str(path))
    return (mt or "").startswith("image/")


def _file_size(path: Path) -> int:
    return path.stat().st_size


@dataclass
class TwitterClient:
    """
    Tweepy v1.1 (API) クライアント。media_upload / chunked upload を使ってツイートを投稿する。
    - 本番: OAuth1.1a（consumer/api key/secret + access token/secret）
    - テスト: dry_run=True でネットワークを叩かず I/O だけ検証
    """
    api: Optional[tweepy.API]
    dry_run: bool = False

    # ===== コンストラクタ群 =====================================================

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
            logger.info("TwitterClient initialized in DRY RUN mode.")
            return

        if not all([api_key, api_secret, access_token, access_secret]):
            raise RuntimeError(
                "Twitter OAuth1.1a credentials are missing. "
                "Provide API_KEY/API_SECRET/ACCESS_TOKEN/ACCESS_SECRET."
            )

        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
        self.api = tweepy.API(auth, wait_on_rate_limit=wait_on_rate_limit)

        # 軽い疎通（認証ミスを早期検知）
        try:
            me = self.api.verify_credentials()
            logger.info("TwitterClient authenticated as @%s", getattr(me, "screen_name", "unknown"))
        except Exception as e:  # noqa: BLE001
            # 215 Bad Authentication data などはここで検知される
            raise RuntimeError(f"Twitter authentication failed: {e}") from e

    @classmethod
    def from_config(cls, config: Dict, *, dry_run: bool) -> "TwitterClient":
        """
        あなたの既存テスト/本番構成に合わせた secret ローダ。
        config の各キーには “シークレット名” を入れ、その中の最初の値を使う。
          - api_key, api_secret, access_token, access_secret
        """
        return cls(
            _first_secret_value(config, "api_key"),
            _first_secret_value(config, "api_secret"),
            _first_secret_value(config, "access_token"),
            _first_secret_value(config, "access_secret"),
            dry_run=dry_run,
        )

    @classmethod
    def from_env(cls, *, dry_run: Optional[bool] = None) -> "TwitterClient":
        """
        環境変数からの生成。X_* と TWITTER_* の両方に対応。
        - X_API_KEY / TWITTER_API_KEY
        - X_API_SECRET / TWITTER_API_SECRET
        - X_ACCESS_TOKEN / TWITTER_ACCESS_TOKEN
        - X_ACCESS_SECRET / TWITTER_ACCESS_TOKEN_SECRET
        """
        if dry_run is None:
            dry_run = os.getenv("TWITTER_DRY_RUN", "0") == "1"

        if dry_run:
            return cls("", "", "", "", dry_run=True)

        ck = _get_env_any("X_API_KEY", "TWITTER_API_KEY")
        cs = _get_env_any("X_API_SECRET", "TWITTER_API_SECRET")
        at = _get_env_any("X_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN")
        ats = _get_env_any("X_ACCESS_SECRET", "TWITTER_ACCESS_TOKEN_SECRET")

        return cls(ck or "", cs or "", at or "", ats or "", dry_run=False)

    # ===== 投稿ロジック =========================================================

    def post(self, text: str, video_path: Path, image_path: Path) -> Dict:
        """
        動画 + 画像（サムネ）を添付してツイート。
        - DRY RUN: ネットワークを叩かず、入力検証のみ行いダミー応答を返す
        - 本番: v1.1 media upload（動画は chunked）、update_status を実行
        """
        if not isinstance(video_path, Path):
            video_path = Path(video_path)
        if not isinstance(image_path, Path):
            image_path = Path(image_path)

        # 入力検証
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if self.dry_run:
            logger.info("[DRY_RUN] tweet: %s", text)
            return {
                "status": text,
                "video": str(video_path),
                "image": str(image_path),
                "dry_run": True,
            }

        assert self.api is not None, "API client not initialized"

        # ---- メディアアップロード
        media_ids: list[str] = []

        # 1) 動画（推奨: yuv420p/h.264）— サイズに応じて chunked
        vid_id = self._upload_video(video_path)
        media_ids.append(vid_id)

        # 2) 画像（png/jpg）— 通常アップロード
        img_id = self._upload_image(image_path)
        media_ids.append(img_id)

        # ---- ツイート本体
        try:
            status = self.api.update_status(status=text, media_ids=media_ids)
        except tweepy.TweepyException as e:
            # 代表例: BadRequest(215) = 認証不備、403 = メディア規約違反、413/400 = エンコード不適合 等
            raise RuntimeError(f"Tweet failed: {e}") from e

        return {
            "id": getattr(status, "id_str", None) or str(getattr(status, "id", "")),
            "text": getattr(status, "text", None) or text,
            "media_ids": media_ids,
        }

    # ===== 内部: アップロード実装 ================================================

    def _upload_image(self, path: Path) -> str:
        if not _is_image(path):
            logger.warning("Image mime-type unknown; attempting upload anyway: %s", path)
        try:
            media = self.api.media_upload(filename=str(path))
            return media.media_id_string
        except tweepy.TweepyException as e:
            raise RuntimeError(f"Image upload failed: {e}") from e

    def _upload_video(self, path: Path) -> str:
        """
        動画は chunked アップロードで頑健に。
        ・ファイルが小さくても chunked に統一しておくと将来 5MB 超でも安全
        ・media_category='tweet_video' を明示
        """
        if not _is_video(path):
            logger.warning("Video mime-type unknown; attempting upload anyway: %s", path)

        total_bytes = _file_size(path)
        media_type, _ = mimetypes.guess_type(str(path))
        if not media_type:
            logger.warning("Could not determine media type for %s, defaulting to video/mp4", path)
            media_type = "video/mp4"

        fp = open(path, "rb")  # noqa: P201
        try:
            init = self.api.chunked_upload_init(
                media_type=media_type,
                total_bytes=total_bytes,
                media_category="tweet_video",
            )
            media_id = init.media_id

            # 4MB チャンクが一般的に安全
            CHUNK = 4 * 1024 * 1024
            segment_id = 0
            fp.seek(0)
            while True:
                chunk = fp.read(CHUNK)
                if not chunk:
                    break
                self.api.chunked_upload_append(
                    file=chunk, media_id=media_id, segment_index=segment_id
                )
                segment_id += 1

            fin = self.api.chunked_upload_finalize(media_id)
            # 処理中（'in_progress'）の場合はポーリング
            state = getattr(fin, "processing_info", {}).get("state", None)
            while state == "in_progress":
                check_after = getattr(fin.processing_info, "check_after_secs", 2)
                time.sleep(check_after)
                fin = self.api.get_media_upload_status(media_id)
                state = getattr(fin, "processing_info", {}).get("state", None)

            if state == "failed":
                err = getattr(fin.processing_info, "error", {})
                raise RuntimeError(f"Video processing failed: {err}")

            return str(media_id)
        except tweepy.TweepyException as e:
            raise RuntimeError(f"Video upload failed: {e}") from e
        finally:
            fp.close()
