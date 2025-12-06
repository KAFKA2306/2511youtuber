import base64
import datetime
import hashlib
import json
import logging
import random
import time
from pathlib import Path
from typing import Dict, Optional

import requests
from pydantic import BaseModel

from src.core.io_utils import load_json, write_text
from src.core.step import Step

logger = logging.getLogger(__name__)


class HatenaConfig(BaseModel):
    hatena_id: str
    blog_id: str  # e.g., "kafkafinancialgroup.hatenablog.com"
    api_key: str
    dry_run: bool = False


class HatenaPoster:
    """
    Handles posting to Hatena Blog using the AtomPub API.
    Uses WSSE Authentication for security.
    """

    def __init__(self, config: HatenaConfig):
        self.config = config
        self.base_url = f"https://blog.hatena.ne.jp/{config.hatena_id}/{config.blog_id}/atom"

    def _generate_wsse_header(self) -> str:
        """Generates the X-WSSE header for authentication."""
        nonce = hashlib.sha1(str(time.time() + random.random()).encode()).digest()
        created = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        nonce_b64 = base64.b64encode(nonce).decode()

        digest = hashlib.sha1((nonce + created.encode() + self.config.api_key.encode())).digest()
        digest_b64 = base64.b64encode(digest).decode()

        return (
            f'UsernameToken Username="{self.config.hatena_id}", '
            f'PasswordDigest="{digest_b64}", Nonce="{nonce_b64}", Created="{created}"'
        )

    def post(self, title: str, content: str, categories: list[str] = None) -> Optional[str]:
        """
        Posts an entry to Hatena Blog.
        Returns the Entry URL if successful, None otherwise.
        """
        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would post to Hatena Blog:\nTitle: {title}\nCategories: {categories}")
            return "https://hatenablog.com/dry_run_entry"

        endpoint = f"{self.base_url}/entry"
        headers = {"X-WSSE": self._generate_wsse_header(), "Content-Type": "application/xml"}

        # Construct Atom XML body
        category_xml = ""
        if categories:
            for cat in categories:
                category_xml += f'<category term="{cat}" />'

        xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
        <entry xmlns="http://www.w3.org/2005/Atom"
               xmlns:app="http://www.w3.org/2007/app">
          <title>{title}</title>
          <content type="text/plain">{content}</content>
          <updated>{datetime.datetime.now().isoformat()}</updated>
          {category_xml}
          <app:control>
            <app:draft>no</app:draft>
          </app:control>
        </entry>
        """

        try:
            resp = requests.post(endpoint, headers=headers, data=xml_body.encode("utf-8"))
            resp.raise_for_status()

            # Parse response to get the link (simplified)
            # In a real scenario, use an XML parser, but for now logging is enough
            logger.info("Successfully posted to Hatena Blog")
            return "https://hatenablog.com/posted_entry"  # Placeholder, real URL is in response

        except Exception as e:
            logger.error(f"Failed to post to Hatena Blog: {e}")
            return None


class HatenaStep(Step):
    name = "post_hatena"
    output_filename = "hatena_post.json"

    def __init__(self, run_id: str, run_dir: Path, config: HatenaConfig):
        super().__init__(run_id, run_dir)
        self.config = config
        self.poster = HatenaPoster(config)

    def execute(self, inputs: Dict[str, Path]) -> Path:
        metadata_path = inputs.get("analyze_metadata")

        if not metadata_path or not metadata_path.exists():
            logger.warning("Metadata not found, skipping Hatena post")
            return Path()

        metadata = load_json(metadata_path)
        title = metadata.get("title", "No Title")
        content = metadata.get("description", "")
        tags = metadata.get("tags", [])

        post_url = self.poster.post(title, content, tags)

        result = {"post_url": post_url, "status": "success" if post_url else "failed"}
        return Path(write_text(self.get_output_path(), json.dumps(result, indent=2)))
