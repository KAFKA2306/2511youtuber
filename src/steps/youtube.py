from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

from src.brand import active_brand, apply_active_brand_to_metadata
from src.core.media_utils import resolve_video_input
from src.core.step import Step
from src.providers.youtube import YouTubeClient


class YouTubeUploader(Step):
    name = "upload_youtube"
    output_filename = "youtube.json"
    is_required = False

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        youtube_config: Dict | None = None,
    ) -> None:
        super().__init__(run_id, run_dir)
        youtube_config = dict(youtube_config or {})
        brand = active_brand()
        if brand is not None:
            if brand["approved"]:
                youtube_config["default_visibility"] = brand["default_visibility"]
            else:
                youtube_config["dry_run"] = True
                youtube_config["default_visibility"] = "private"

        self.client = YouTubeClient(
            dry_run=bool(youtube_config.get("dry_run", True)),
            default_visibility=youtube_config.get("default_visibility", "unlisted"),
            category_id=int(youtube_config.get("category_id", 24)),
            default_tags=youtube_config.get("default_tags", []),
            max_title_length=int(youtube_config.get("max_title_length", 100)),
            max_description_length=int(youtube_config.get("max_description_length", 5000)),
        )

    def execute(self, inputs: Dict[str, Path]) -> Path:
        video_path = resolve_video_input(inputs)
        metadata_value = inputs.get("analyze_metadata")
        if not metadata_value:
            raise ValueError("Metadata file not found for YouTube upload")

        metadata_path = Path(metadata_value)
        if not metadata_path.exists():
            raise ValueError("Metadata file not found for YouTube upload")

        with open(metadata_path, encoding="utf-8") as f:
            metadata = apply_active_brand_to_metadata(json.load(f))

        thumbnail_input = inputs.get("generate_thumbnail")
        thumbnail_path = Path(thumbnail_input) if thumbnail_input else None
        if thumbnail_path and (
            not thumbnail_path.exists() or thumbnail_path.stat().st_size == 0
        ):
            thumbnail_path = None

        upload_result = self.client.upload(
            Path(video_path), metadata, thumbnail_path=thumbnail_path
        )
        if brand := active_brand():
            approved = bool(brand["approved"])
            if not approved and upload_result.get("external_side_effect") is True:
                raise RuntimeError("Unapproved branded run attempted an external publish")
            upload_result["review"] = {
                "status": "approved" if approved else "pending",
                "approved": approved,
                "brand": {
                    "schema_version": brand["schema_version"],
                    "brand_id": brand["brand_id"],
                    "display_name": brand["display_name"],
                    "config_sha256": brand["config_sha256"],
                    "default_visibility": brand["default_visibility"],
                },
                "approval": brand.get("approval"),
                "sources": self._source_evidence(inputs.get("collect_news")),
                "artifacts": {
                    "script": self._artifact_evidence(inputs.get("generate_script")),
                    "video": self._artifact_evidence(Path(video_path)),
                    "metadata": self._artifact_evidence(metadata_path),
                },
            }

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(upload_result, f, ensure_ascii=False, indent=2)

        return output_path

    @staticmethod
    def _artifact_evidence(value: Path | None) -> dict[str, Any] | None:
        if not value:
            return None
        path = Path(value)
        if not path.exists() or not path.is_file():
            return None
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return {
            "path": str(path),
            "sha256": digest.hexdigest(),
            "size_bytes": path.stat().st_size,
        }

    @staticmethod
    def _source_evidence(news_value: Path | None) -> list[dict[str, str]]:
        if not news_value:
            return []
        news_path = Path(news_value)
        if not news_path.exists():
            return []
        items = json.loads(news_path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            return []
        evidence = []
        for item in items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            row = {"url": url}
            title = str(item.get("title", "")).strip()
            published_at = str(item.get("published_at", "")).strip()
            if title:
                row["title"] = title
            if published_at:
                row["published_at"] = published_at
            evidence.append(row)
        return evidence
