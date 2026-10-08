import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.brand import (
    activate_brand_profile,
    active_brand,
    apply_active_brand_to_metadata,
    clear_active_brand,
    validate_active_brand_topic,
)
from src.steps.youtube import YouTubeUploader


class BrandProfileTests(unittest.TestCase):
    def tearDown(self):
        clear_active_brand()

    def _profile(
        self,
        directory: str,
        *,
        rights_confirmed: bool = True,
    ) -> Path:
        path = Path(directory) / "brand.yaml"
        path.write_text(
            "schema_version: 1\n"
            "brand_id: example-financial-media\n"
            "display_name: Example Financial Media\n"
            "disclosure_text: 公開前レビュー用のサンプルです。\n"
            "allowed_topics:\n"
            "  - 半導体\n"
            "  - AI\n"
            "default_visibility: private\n"
            "intro:\n"
            "  path: assets/brand/intro.mp4\n"
            f"  rights_confirmed: {str(rights_confirmed).lower()}\n"
            "outro: null\n",
            encoding="utf-8",
        )
        return path

    def _approval(self, directory: str, profile_path: Path, *, digest: str | None = None) -> Path:
        path = Path(directory) / "approval.json"
        config_digest = digest or hashlib.sha256(profile_path.read_bytes()).hexdigest()
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "brand_id": "example-financial-media",
                    "brand_config_sha256": config_digest,
                    "approved": True,
                    "approved_by": "reviewer",
                    "approved_at": "2026-10-08T20:00:00+09:00",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def test_profile_adds_versioned_brand_metadata_and_visibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._profile(tmp)
            with patch.dict(os.environ, {}, clear=True):
                activate_brand_profile(path)
                branded = apply_active_brand_to_metadata(
                    {"title": "市場まとめ", "description": "説明", "tags": ["金融"]}
                )
                brand = active_brand()

        self.assertEqual(branded["title"], "Example Financial Media | 市場まとめ")
        self.assertIn("公開前レビュー用のサンプルです。", branded["description"])
        self.assertEqual(branded["visibility"], "private")
        self.assertEqual(branded["brand"]["schema_version"], 1)
        self.assertEqual(len(brand["config_sha256"]), 64)
        self.assertFalse(brand["approved"])

    def test_unconfirmed_brand_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._profile(tmp, rights_confirmed=False)
            with self.assertRaisesRegex(ValueError, "rights_confirmed=true"):
                activate_brand_profile(path)

    def test_allowed_topics_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._profile(tmp)
            activate_brand_profile(path)
            validate_active_brand_topic("AI 半導体 決算")
            with self.assertRaisesRegex(ValueError, "outside allowed_topics"):
                validate_active_brand_topic("不動産 REIT")

    def test_approval_must_match_exact_brand_config_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self._profile(tmp)
            bad = self._approval(tmp, profile, digest="0" * 64)
            with self.assertRaisesRegex(ValueError, "does not match"):
                activate_brand_profile(profile, approval_path=bad)

            good = self._approval(tmp, profile)
            activate_brand_profile(profile, approval_path=good)
            brand = active_brand()

        self.assertTrue(brand["approved"])
        self.assertEqual(brand["approval"]["approved_by"], "reviewer")

    def test_pending_brand_run_produces_traceable_dry_run_review_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self._profile(tmp)
            activate_brand_profile(profile)

            run_dir = Path(tmp) / "runs"
            inputs_dir = Path(tmp) / "inputs"
            inputs_dir.mkdir()
            video = inputs_dir / "video.mp4"
            video.write_bytes(b"not-empty")
            script = inputs_dir / "script.json"
            script.write_text('{"segments": []}', encoding="utf-8")
            metadata = inputs_dir / "metadata.json"
            metadata.write_text(
                json.dumps({"title": "市場まとめ", "description": "説明"}),
                encoding="utf-8",
            )
            news = inputs_dir / "news.json"
            news.write_text(
                json.dumps(
                    [
                        {
                            "title": "AI半導体",
                            "url": "https://example.com/source",
                            "published_at": "2026-10-08",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            uploader = YouTubeUploader(
                run_id="test",
                run_dir=run_dir,
                youtube_config={"dry_run": False, "default_visibility": "public"},
            )
            result_path = uploader.execute(
                {
                    "render_video": video,
                    "generate_script": script,
                    "analyze_metadata": metadata,
                    "collect_news": news,
                }
            )
            payload = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "dry_run")
        self.assertFalse(payload["external_side_effect"])
        self.assertEqual(payload["review"]["status"], "pending")
        self.assertFalse(payload["review"]["approved"])
        self.assertEqual(payload["review"]["sources"][0]["url"], "https://example.com/source")
        for key in ("script", "video", "metadata"):
            self.assertEqual(len(payload["review"]["artifacts"][key]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
