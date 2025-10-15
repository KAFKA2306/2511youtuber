from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote

import requests

from src.utils.secrets import load_secret_values


class TwitterClient:
    upload_url = "https://upload.twitter.com/1.1/media/upload.json"
    tweet_url = "https://api.twitter.com/2/tweets"

    def __init__(
        self,
        *,
        api_key_key: str = "TWITTER_API_KEY",
        api_secret_key: str = "TWITTER_API_SECRET",
        access_token_key: str = "TWITTER_ACCESS_TOKEN",
        access_secret_key: str = "TWITTER_ACCESS_SECRET",
    ) -> None:
        self.api_key = self._secret(api_key_key)
        self.api_secret = self._secret(api_secret_key)
        self.access_token = self._secret(access_token_key)
        self.access_secret = self._secret(access_secret_key)

    def post_video(
        self,
        *,
        text: str,
        video_path: Path,
        thumbnail_path: Path | None = None,
        chunk_size: int = 5_242_880,
    ) -> Dict[str, Any]:
        video_id = self._upload_video(video_path, chunk_size)
        media_ids = [video_id]
        thumbnail_id = None
        if thumbnail_path and thumbnail_path.exists():
            thumbnail_id = self._upload_image(thumbnail_path)
            media_ids.append(thumbnail_id)
        tweet = self._post_json(self.tweet_url, {"text": text, "media": {"media_ids": media_ids}})
        return {"tweet": tweet, "video_media_id": video_id, "thumbnail_media_id": thumbnail_id}

    def _secret(self, key: str) -> str:
        return load_secret_values(key)[0]

    def _upload_video(self, path: Path, chunk_size: int) -> str:
        size = path.stat().st_size
        init = self._post_form(
            self.upload_url,
            {
                "command": "INIT",
                "total_bytes": size,
                "media_type": "video/mp4",
                "media_category": "tweet_video",
            },
        )
        media_id = init["media_id_string"]
        segment = 0
        with path.open("rb") as src:
            while True:
                chunk = src.read(chunk_size)
                if not chunk:
                    break
                self._post_form(
                    self.upload_url,
                    {
                        "command": "APPEND",
                        "media_id": media_id,
                        "segment_index": segment,
                    },
                    {"media": (path.name, chunk)},
                )
                segment += 1
        finalize = self._post_form(self.upload_url, {"command": "FINALIZE", "media_id": media_id})
        info = finalize.get("processing_info")
        while info and info.get("state") in {"pending", "in_progress"}:
            time.sleep(info.get("check_after_secs", 1))
            status = self._get(self.upload_url, {"command": "STATUS", "media_id": media_id})
            info = status.get("processing_info")
        return media_id

    def _upload_image(self, path: Path) -> str:
        with path.open("rb") as src:
            content = src.read()
        response = self._post_form(
            self.upload_url,
            {"media_category": "tweet_image"},
            {"media": (path.name, content)},
        )
        return response["media_id_string"]

    def _oauth_headers(self, method: str, url: str, params: Dict[str, Any] | None = None) -> Dict[str, str]:
        params = {str(k): str(v) for k, v in (params or {}).items()}
        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_nonce": base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("="),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self.access_token,
            "oauth_version": "1.0",
        }
        signature_params = dict(params)
        signature_params.update(oauth_params)
        items = sorted((quote(k, safe="~"), quote(v, safe="~")) for k, v in signature_params.items())
        param_str = "&".join(f"{k}={v}" for k, v in items)
        base_elems = [method.upper(), quote(url, safe="~"), quote(param_str, safe="~")]
        base_string = "&".join(base_elems)
        signing_key = "&".join([quote(self.api_secret, safe="~"), quote(self.access_secret, safe="~")])
        digest = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        oauth_params["oauth_signature"] = base64.b64encode(digest).decode()
        header = "OAuth " + ", ".join(
            f'{key}="{quote(value, safe="~")}"' for key, value in sorted(oauth_params.items())
        )
        return {"Authorization": header}

    def _post_form(
        self,
        url: str,
        data: Dict[str, Any],
        files: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        payload = {str(k): str(v) for k, v in data.items()}
        headers = self._oauth_headers("POST", url, payload)
        response = requests.post(url, data=payload, files=files, headers=headers)
        response.raise_for_status()
        return response.json()

    def _post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = self._oauth_headers("POST", url, {})
        headers["Content-Type"] = "application/json"
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def _get(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        query = {str(k): str(v) for k, v in params.items()}
        headers = self._oauth_headers("GET", url, query)
        response = requests.get(url, params=query, headers=headers)
        response.raise_for_status()
        return response.json()
