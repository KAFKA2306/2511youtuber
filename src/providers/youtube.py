from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
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


class PublicationGateError(RuntimeError):
    pass


class YouTubeClient:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    EXTERNAL_APPROVAL_ENV = "YOUTUBE_EXTERNAL_PUBLISH_APPROVED"
    PUBLIC_APPROVAL_ENV = "YOUTUBE_PUBLIC_VISIBILITY_APPROVED"
    APPROVAL_VALUE = "I_UNDERSTAND_THIS_UPLOADS_EXTERNALLY"
    PUBLIC_APPROVAL_VALUE = "I_UNDERSTAND_THIS_WILL_BE_PUBLIC"

    def __init__(
        self,
        *,
        dry_run: bool = True,
        default_visibility: str = "private",
        category_id: int = 25,
        default_tags: Iterable[str] | None = None,
        max_title_length: int = 100,
        max_description_length: int = 5000,
        token_file: str | Path = "token.json",
    ):
        self.dry_run = bool(dry_run)
        self.default_visibility = self._validate_visibility(default_visibility)
        self.category_id = int(category_id)
        self.default_tags = list(default_tags or [])
        self.max_title_length = int(max_title_length)
        self.max_description_length = int(max_description_length)
        self.token_file = Path(token_file)
        self.service = None

        if self.max_title_length < 1 or self.max_description_length < 1:
            raise ValueError("metadata length limits must be positive")

        if not self.dry_run:
            self._require_external_approval()
            if self.default_visibility == "public":
                self._require_public_approval()
            creds = self._get_credentials()
            if not creds:
                raise ValueError("Failed to obtain YouTube OAuth credentials")
            self.service = build("youtube", "v3", credentials=creds)
            logger.info("YouTube API service initialized after explicit publication approval")

    @staticmethod
    def _validate_visibility(value: str) -> str:
        visibility = str(value).strip().lower()
        if visibility not in {"private", "unlisted", "public"}:
            raise ValueError(f"Invalid YouTube visibility: {value!r}")
        return visibility

    @classmethod
    def _require_external_approval(cls) -> None:
        if os.getenv(cls.EXTERNAL_APPROVAL_ENV) != cls.APPROVAL_VALUE:
            raise PublicationGateError(
                "External YouTube upload is blocked. Keep dry_run=true, or set "
                f"{cls.EXTERNAL_APPROVAL_ENV}={cls.APPROVAL_VALUE!r} for this process "
                "after reviewing the rendered video, metadata, sources, and rights."
            )

    @classmethod
    def _require_public_approval(cls) -> None:
        if os.getenv(cls.PUBLIC_APPROVAL_ENV) != cls.PUBLIC_APPROVAL_VALUE:
            raise PublicationGateError(
                "Public visibility is blocked. Use private/unlisted, or set "
                f"{cls.PUBLIC_APPROVAL_ENV}={cls.PUBLIC_APPROVAL_VALUE!r} for this "
                "process after an explicit public-release decision."
            )

    def _get_credentials(self) -> Credentials:
        creds = None
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_file), self.SCOPES
                )
            except (ValueError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"Invalid YouTube credential cache: {self.token_file}"
                ) from exc
            if creds and not self._has_required_scopes(creds):
                creds = None

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("Refreshed YouTube credentials")
        if not creds or not creds.valid:
            creds = self._run_oauth_flow()
        if creds:
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
            try:
                self.token_file.chmod(0o600)
            except OSError:
                logger.warning("Could not restrict permissions on YouTube token cache")
        return creds

    def _has_required_scopes(self, creds: Credentials) -> bool:
        scopes = set(creds.scopes or ())
        return all(scope in scopes for scope in self.SCOPES)

    def _run_oauth_flow(self) -> Credentials:
        client_id = load_secret_values("YOUTUBE_CLIENT_ID")
        client_secret = load_secret_values("YOUTUBE_CLIENT_SECRET")
        project_id = load_secret_values("YOUTUBE_PROJECT_ID")
        if not client_id or not client_secret:
            raise ValueError("YouTube OAuth credentials not found in environment")
        config = {
            "installed": {
                "client_id": client_id[0],
                "client_secret": client_secret[0],
                "project_id": project_id[0] if project_id else "youtube-project",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(config, self.SCOPES)
        logger.info("Opening browser for YouTube OAuth authentication")
        return flow.run_local_server(port=8080)

    def prepare_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        prepared = dict(metadata)
        prepared["title"] = self._trim(
            str(prepared.get("title", "")).strip(), self.max_title_length
        )
        prepared["description"] = self._trim(
            str(prepared.get("description", "")).strip(),
            self.max_description_length,
        )
        if not prepared["title"]:
            raise ValueError("YouTube title must not be empty")
        if not prepared["description"]:
            raise ValueError("YouTube description must not be empty")
        prepared["tags"] = self._merge_tags(prepared.get("tags", []))
        prepared["visibility"] = self._validate_visibility(
            prepared.get("visibility", self.default_visibility)
        )
        prepared.setdefault("category_id", self.category_id)
        if prepared["visibility"] == "public" and not self.dry_run:
            self._require_public_approval()
        return prepared

    def upload(
        self,
        video_path: Path,
        metadata: Dict[str, Any],
        thumbnail_path: Path | None = None,
    ) -> Dict[str, Any]:
        video_path = Path(video_path)
        if not video_path.exists() or not video_path.is_file():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if video_path.stat().st_size == 0:
            raise ValueError("Video file is empty")

        prepared = self.prepare_metadata(metadata)
        thumbnail = Path(thumbnail_path) if thumbnail_path else None
        if thumbnail and (not thumbnail.exists() or not thumbnail.is_file()):
            raise FileNotFoundError(f"Thumbnail file not found: {thumbnail}")
        if thumbnail and thumbnail.stat().st_size == 0:
            thumbnail = None

        if self.dry_run:
            return {
                "video_id": self._dry_run_id(video_path, prepared),
                "status": "dry_run",
                "external_side_effect": False,
                "metadata": prepared,
                "thumbnail_path": str(thumbnail) if thumbnail else None,
            }

        self._require_external_approval()
        if prepared["visibility"] == "public":
            self._require_public_approval()
        if self.service is None:
            raise PublicationGateError("YouTube service is not initialized")

        body = {
            "snippet": {
                "title": prepared["title"],
                "description": prepared["description"],
                "tags": prepared["tags"],
                "categoryId": str(prepared["category_id"]),
            },
            "status": {
                "privacyStatus": prepared["visibility"],
                "selfDeclaredMadeForKids": False,
            },
        }
        file_size = video_path.stat().st_size
        logger.info(
            "Uploading reviewed video: %s (%s bytes, visibility=%s)",
            video_path,
            file_size,
            prepared["visibility"],
        )
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        response = (
            self.service.videos()
            .insert(part="snippet,status", body=body, media_body=media)
            .execute()
        )
        video_id = response.get("id")
        if not video_id:
            raise RuntimeError("YouTube API response did not include a video id")

        if thumbnail:
            thumb_media = MediaFileUpload(str(thumbnail), mimetype="image/png")
            self.service.thumbnails().set(
                videoId=video_id, media_body=thumb_media
            ).execute()

        return {
            "video_id": video_id,
            "status": "uploaded",
            "external_side_effect": True,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "uploaded_at_utc": datetime.now(timezone.utc).isoformat(),
            "file_size": file_size,
            "metadata": prepared,
            "thumbnail_path": str(thumbnail) if thumbnail else None,
        }

    def _merge_tags(self, tags: Iterable[str]) -> List[str]:
        seen = set()
        merged = []
        for tag in list(self.default_tags) + list(tags):
            clean = str(tag).strip()
            if clean and clean not in seen:
                merged.append(clean)
                seen.add(clean)
        return merged

    @staticmethod
    def _trim(text: str, limit: int) -> str:
        return text if len(text) <= limit else text[: max(limit - 1, 0)] + "…"

    @staticmethod
    def _dry_run_id(video_path: Path, metadata: Dict[str, Any]) -> str:
        digest = hashlib.sha256()
        digest.update(video_path.name.encode("utf-8"))
        digest.update(str(video_path.stat().st_size).encode("utf-8"))
        digest.update(metadata.get("title", "").encode("utf-8"))
        return "dry_" + digest.hexdigest()[:16]
