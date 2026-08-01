import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.providers.youtube import PublicationGateError, YouTubeClient


class YouTubePublicationGateTests(unittest.TestCase):
    def test_non_dry_run_requires_explicit_external_approval(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PublicationGateError):
                YouTubeClient(dry_run=False, default_visibility="private")

    def test_public_visibility_requires_separate_approval(self) -> None:
        env = {
            YouTubeClient.EXTERNAL_APPROVAL_ENV: YouTubeClient.APPROVAL_VALUE,
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(PublicationGateError):
                YouTubeClient(dry_run=False, default_visibility="public")

    def test_dry_run_has_no_external_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "video.mp4"
            video.write_bytes(b"not-empty-test-video")
            client = YouTubeClient(dry_run=True, default_visibility="private")
            result = client.upload(
                video,
                {
                    "title": "監査用タイトル",
                    "description": "監査用説明",
                    "tags": ["audit"],
                },
            )
            self.assertEqual(result["status"], "dry_run")
            self.assertFalse(result["external_side_effect"])
            self.assertTrue(result["video_id"].startswith("dry_"))

    def test_empty_video_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "empty.mp4"
            video.touch()
            client = YouTubeClient(dry_run=True)
            with self.assertRaises(ValueError):
                client.upload(
                    video,
                    {"title": "title", "description": "description"},
                )

    def test_empty_metadata_is_rejected(self) -> None:
        client = YouTubeClient(dry_run=True)
        with self.assertRaises(ValueError):
            client.prepare_metadata({"title": "", "description": "description"})
        with self.assertRaises(ValueError):
            client.prepare_metadata({"title": "title", "description": ""})


if __name__ == "__main__":
    unittest.main()
