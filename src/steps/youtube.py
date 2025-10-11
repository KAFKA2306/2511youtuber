from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from src.providers.youtube import YouTubeClient
from src.steps.base import Step


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
        youtube_config = youtube_config or {}

        self.client = YouTubeClient(
            dry_run=bool(youtube_config.get("dry_run", True)),
            default_visibility=youtube_config.get("default_visibility", "unlisted"),
            category_id=int(youtube_config.get("category_id", 24)),
            default_tags=youtube_config.get("default_tags", []),
            max_title_length=int(youtube_config.get("max_title_length", 100)),
            max_description_length=int(youtube_config.get("max_description_length", 5000)),
        )

    def execute(self, inputs: Dict[str, Path]) -> Path:
        video_path = inputs.get("render_video")
        metadata_path = inputs.get("analyze_metadata")

        if not video_path or not Path(video_path).exists():
            raise ValueError("Video file not found for YouTube upload")
        if not metadata_path or not Path(metadata_path).exists():
            raise ValueError("Metadata file not found for YouTube upload")

        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)

        thumbnail_input = inputs.get("generate_thumbnail")
        thumbnail_path = Path(thumbnail_input) if thumbnail_input else None
        if thumbnail_path and (not thumbnail_path.exists() or thumbnail_path.stat().st_size == 0):
            thumbnail_path = None

        upload_result = self.client.upload(Path(video_path), metadata, thumbnail_path=thumbnail_path)

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(upload_result, f, ensure_ascii=False, indent=2)

        return output_path
