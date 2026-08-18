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
)


class BrandProfileTests(unittest.TestCase):
    def tearDown(self):
        clear_active_brand()

    def _profile(self, directory: str) -> Path:
        path = Path(directory) / "brand.yaml"
        path.write_text(
            "brand_id: example-financial-media\n"
            "display_name: Example Financial Media\n"
            "disclosure_text: 公開前レビュー用のサンプルです。\n",
            encoding="utf-8",
        )
        return path

    def test_profile_adds_brand_metadata_with_config_hash(self):
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
        self.assertEqual(branded["brand"]["brand_id"], "example-financial-media")
        self.assertEqual(len(branded["brand"]["config_sha256"]), 64)
        self.assertEqual(brand["config_sha256"], branded["brand"]["config_sha256"])

    def test_unknown_brand_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._profile(tmp)
            path.write_text(
                path.read_text(encoding="utf-8") + "unsupported_setting: true\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                activate_brand_profile(path)

    def test_brand_cli_and_uploader_keep_customer_runs_non_publishing(self):
        main_source = Path("src/main.py").read_text(encoding="utf-8")
        uploader_source = Path("src/steps/youtube.py").read_text(encoding="utf-8")

        self.assertIn('"--brand-config"', main_source)
        self.assertIn(
            "review_only = args.dry_run or args.brand_config is not None", main_source
        )
        self.assertIn("_configure_publication_mode(dry_run=review_only)", main_source)
        self.assertIn('youtube_config["dry_run"] = True', uploader_source)
        self.assertIn('youtube_config["default_visibility"] = "private"', uploader_source)
        self.assertIn('"approved": False', uploader_source)
        self.assertIn('"sources": self._source_evidence', uploader_source)


if __name__ == "__main__":
    unittest.main()
