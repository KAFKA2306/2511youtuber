from __future__ import annotations

import hashlib
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.utils.logger import get_logger
from src.utils.secrets import load_secret_values

logger = get_logger(__name__)


class YouTubeClient:
    """YouTube Data API client with OAuth authentication.

    Supports both dry-run mode for testing and real uploads with OAuth2.0.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]

    def __init__(
        self,
        *,
        dry_run: bool = True,
        default_visibility: str = "unlisted",
        category_id: int = 25,
        default_tags: Iterable[str] | None = None,
        max_title_length: int = 100,
        max_description_length: int = 5000,
    ) -> None:
        self.dry_run = dry_run
        self.default_visibility = default_visibility
        self.category_id = category_id
        self.default_tags = list(default_tags or [])
        self.max_title_length = max_title_length
        self.max_description_length = max_description_length
        self.service = None

        if not self.dry_run:
            self._setup_service()

    def _setup_service(self):
        credentials = self._get_credentials()
        if not credentials:
            raise ValueError("Failed to obtain YouTube OAuth credentials")

        self.service = build("youtube", "v3", credentials=credentials)
        logger.info("YouTube API service initialized")

    def _get_credentials(self) -> Credentials:
        token_file = "token.pickle"
        creds = None

        if os.path.exists(token_file):
            with open(token_file, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Refreshed YouTube credentials")
            else:
                creds = self._run_oauth_flow()

            if creds:
                with open(token_file, "wb") as token:
                    pickle.dump(creds, token)

        return creds

    def _run_oauth_flow(self) -> Credentials:
        client_id_list = load_secret_values("YOUTUBE_CLIENT_ID")
        client_secret_list = load_secret_values("YOUTUBE_CLIENT_SECRET")
        project_id_list = load_secret_values("YOUTUBE_PROJECT_ID")

        if not client_id_list or not client_secret_list:
            raise ValueError("YouTube OAuth credentials not found in environment")

        client_config = {
            "installed": {
                "client_id": client_id_list[0],
                "client_secret": client_secret_list[0],
                "project_id": project_id_list[0] if project_id_list else "youtube-project",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"],
            }
        }

        flow = InstalledAppFlow.from_client_config(client_config, self.SCOPES)
        logger.info("Opening browser for YouTube OAuth authentication...")
        creds = flow.run_local_server(port=8080)
        logger.info("YouTube OAuth authentication completed")

        return creds

    def prepare_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and enrich metadata before uploading."""

        prepared: Dict[str, Any] = dict(metadata)

        prepared["title"] = self._trim(prepared.get("title", ""), self.max_title_length)
        prepared["description"] = self._trim(
            prepared.get("description", ""),
            self.max_description_length,
        )

        merged_tags = self._merge_tags(prepared.get("tags", []))
        prepared["tags"] = merged_tags

        prepared.setdefault("visibility", self.default_visibility)
        prepared.setdefault("category_id", self.category_id)

        return prepared

    def upload(self, video_path: Path, metadata: Dict[str, Any], thumbnail_path: Path | None = None) -> Dict[str, Any]:
        """Upload a video using the prepared metadata.

        In dry-run mode, this generates a deterministic video ID that mimics the
        structure of YouTube IDs while avoiding any network operations.
        """

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        prepared = self.prepare_metadata(metadata)
        thumbnail = Path(thumbnail_path) if thumbnail_path else None
        if thumbnail and not thumbnail.exists():
            raise FileNotFoundError(f"Thumbnail file not found: {thumbnail}")
        if thumbnail and thumbnail.stat().st_size == 0:
            thumbnail = None

        if self.dry_run:
            video_id = self._generate_dry_run_id(video_path, prepared)
            return {
                "video_id": video_id,
                "status": "dry_run",
                "metadata": prepared,
                "thumbnail_path": str(thumbnail) if thumbnail else None,
            }

        upload_body = {
            "snippet": {
                "title": prepared["title"],
                "description": prepared["description"],
                "tags": prepared["tags"],
                "categoryId": str(prepared["category_id"]),
            },
            "status": {"privacyStatus": prepared["visibility"], "selfDeclaredMadeForKids": False},
        }

        file_size = video_path.stat().st_size
        logger.info(f"Uploading video: {video_path} ({file_size} bytes)")

        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        insert_request = self.service.videos().insert(part="snippet,status", body=upload_body, media_body=media)

        response = insert_request.execute()
        video_id = response.get("id")

        if thumbnail:
            thumbnail_media = MediaFileUpload(str(thumbnail), mimetype="image/png")
            self.service.thumbnails().set(videoId=video_id, media_body=thumbnail_media).execute()

        logger.info(f"Video uploaded successfully: {video_id}")

        return {
            "video_id": video_id,
            "status": "uploaded",
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "uploaded_at": datetime.now().isoformat(),
            "file_size": file_size,
            "metadata": prepared,
            "thumbnail_path": str(thumbnail) if thumbnail else None,
        }

    def _merge_tags(self, tags: Iterable[str]) -> List[str]:
        seen = set()
        merged: List[str] = []
        for tag in list(self.default_tags) + list(tags):
            clean = tag.strip()
            if not clean or clean in seen:
                continue
            merged.append(clean)
            seen.add(clean)
        return merged

    def _trim(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: max(limit - 1, 0)] + "…"

    def _generate_dry_run_id(self, video_path: Path, metadata: Dict[str, Any]) -> str:
        digest = hashlib.sha1()
        digest.update(video_path.name.encode("utf-8"))
        digest.update(str(video_path.stat().st_size).encode("utf-8"))
        digest.update(metadata.get("title", "").encode("utf-8"))
        return "dry_" + digest.hexdigest()[:16]
