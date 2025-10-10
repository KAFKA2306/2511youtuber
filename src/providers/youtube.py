from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List


class YouTubeClient:
    """Lightweight client that simulates interactions with the YouTube Data API.

    The real API integration requires OAuth credentials and HTTP requests.
    For Phase 2 we focus on preparing upload metadata and providing a
    deterministic dry-run mode that can be validated via unit and integration
    tests without external network calls.
    """

    def __init__(
        self,
        *,
        dry_run: bool = True,
        default_visibility: str = "unlisted",
        category_id: int = 24,
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

    def upload(self, video_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a video using the prepared metadata.

        In dry-run mode, this generates a deterministic video ID that mimics the
        structure of YouTube IDs while avoiding any network operations.
        """

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        prepared = self.prepare_metadata(metadata)

        if self.dry_run:
            video_id = self._generate_dry_run_id(video_path, prepared)
            return {
                "video_id": video_id,
                "status": "dry_run",
                "metadata": prepared,
            }

        # Placeholder for future real API call implementation.
        video_id = self._generate_dry_run_id(video_path, prepared)
        return {
            "video_id": video_id,
            "status": "uploaded",
            "metadata": prepared,
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

