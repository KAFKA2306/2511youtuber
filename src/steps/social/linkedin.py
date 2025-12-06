import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

import requests
from pydantic import BaseModel

from src.core.io_utils import load_json, write_text
from src.core.step import Step

logger = logging.getLogger(__name__)


class LinkedInConfig(BaseModel):
    access_token: str
    author_urn: str  # e.g., "urn:li:person:..." or "urn:li:organization:..."
    dry_run: bool = False


class LinkedInPoster:
    """
    Handles posting to LinkedIn using the Official API (v2/ugcPosts).
    Supports text-only and image shares.
    """

    API_BASE = "https://api.linkedin.com/v2"

    def __init__(self, config: LinkedInConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

    def post(self, text: str, image_path: Optional[str] = None) -> Optional[str]:
        """
        Posts content to LinkedIn.
        Returns the URN of the created post, or None if failed/dry-run.
        """
        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would post to LinkedIn:\nText: {text}\nImage: {image_path}")
            return "urn:li:share:dry_run"

        try:
            asset_urn = None
            if image_path and os.path.exists(image_path):
                asset_urn = self._upload_image(image_path)

            return self._create_ugc_post(text, asset_urn)

        except Exception as e:
            logger.error(f"Failed to post to LinkedIn: {e}")
            return None

    def _upload_image(self, image_path: str) -> Optional[str]:
        """
        Uploads an image to LinkedIn and returns the Asset URN.
        Flow: Register Upload -> Upload Binary -> Verify (Implicit)
        """
        # 1. Register Upload
        register_url = f"{self.API_BASE}/assets?action=registerUpload"
        register_body = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": self.config.author_urn,
                "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}],
            }
        }

        resp = requests.post(register_url, headers=self.headers, json=register_body)
        resp.raise_for_status()
        data = resp.json()

        upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"][
            "uploadUrl"
        ]
        asset_urn = data["value"]["asset"]

        # 2. Upload Binary
        with open(image_path, "rb") as f:
            upload_resp = requests.put(
                upload_url, headers={"Authorization": f"Bearer {self.config.access_token}"}, data=f
            )
            upload_resp.raise_for_status()

        logger.info(f"Uploaded image to LinkedIn: {asset_urn}")
        return asset_urn

    def _create_ugc_post(self, text: str, asset_urn: Optional[str]) -> str:
        """
        Creates a UGC Post.
        """
        url = f"{self.API_BASE}/ugcPosts"

        share_media_category = "NONE"
        media = []

        if asset_urn:
            share_media_category = "IMAGE"
            media = [
                {"status": "READY", "description": {"text": "Image"}, "media": asset_urn, "title": {"text": "Image"}}
            ]

        body = {
            "author": self.config.author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": share_media_category,
                    "media": media,
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        resp = requests.post(url, headers=self.headers, json=body)
        resp.raise_for_status()

        post_urn = resp.json().get("id")
        logger.info(f"Created LinkedIn post: {post_urn}")
        return post_urn


class LinkedInStep(Step):
    name = "post_linkedin"
    output_filename = "linkedin_post.json"

    def __init__(self, run_id: str, run_dir: Path, config: LinkedInConfig):
        super().__init__(run_id, run_dir)
        self.config = config
        self.poster = LinkedInPoster(config)

    def execute(self, inputs: Dict[str, Path]) -> Path:
        metadata_path = inputs.get("analyze_metadata")
        thumbnail_path = inputs.get("generate_thumbnail")

        if not metadata_path or not metadata_path.exists():
            logger.warning("Metadata not found, skipping LinkedIn post")
            return Path()

        metadata = load_json(metadata_path)
        text = f"{metadata.get('title', '')}\n\n{metadata.get('description', '')}"

        image_path = str(thumbnail_path) if thumbnail_path and thumbnail_path.exists() else None

        post_urn = self.poster.post(text, image_path)

        result = {"post_urn": post_urn, "status": "success" if post_urn else "failed"}
        return Path(write_text(self.get_output_path(), json.dumps(result, indent=2)))
