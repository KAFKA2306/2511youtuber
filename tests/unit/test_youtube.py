import base64
from pathlib import Path

import pytest

from src.providers.youtube import YouTubeClient

pytestmark = pytest.mark.unit


class TestYouTubeClient:
    def test_prepare_metadata_trims_and_merges_tags(self, tmp_path: Path):
        client = YouTubeClient(
            dry_run=True,
            default_visibility="private",
            category_id=28,
            default_tags=["金融", "ニュース"],
            max_title_length=10,
            max_description_length=20,
        )

        prepared = client.prepare_metadata(
            {
                "title": "とても長いタイトルでテストします",
                "description": "説明文もかなり長めに設定してテスト",
                "tags": ["ニュース", "市場"],
            }
        )

        assert len(prepared["title"]) <= 10
        assert len(prepared["description"]) <= 20
        assert prepared["tags"][0] == "金融"
        assert "市場" in prepared["tags"]
        assert prepared["visibility"] == "private"
        assert prepared["category_id"] == 28

    def test_upload_generates_dry_run_id(self, tmp_path: Path):
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"video")

        client = YouTubeClient(dry_run=True)
        result = client.upload(video_path, {"title": "テスト"})

        assert result["status"] == "dry_run"
        assert result["video_id"].startswith("dry_")
        assert result["metadata"]["title"].startswith("テスト")

    def test_upload_includes_thumbnail_path_in_dry_run(self, tmp_path: Path):
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"video")
        thumbnail_path = tmp_path / "thumbnail.png"
        thumbnail_path.write_bytes(
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
            )
        )

        client = YouTubeClient(dry_run=True)
        result = client.upload(video_path, {"title": "テスト"}, thumbnail_path=thumbnail_path)

        assert result["thumbnail_path"] == str(thumbnail_path)

    def test_upload_raises_when_thumbnail_missing(self, tmp_path: Path):
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"video")

        client = YouTubeClient(dry_run=True)

        with pytest.raises(FileNotFoundError):
            client.upload(video_path, {"title": "テスト"}, thumbnail_path=tmp_path / "missing.png")
