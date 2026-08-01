from pathlib import Path
import unittest

import yaml

from src.utils.config import Config


class DefaultConfigSafetyTests(unittest.TestCase):
    def test_raw_yaml_has_no_duplicate_news_key(self):
        text = Path("config/default.yaml").read_text(encoding="utf-8")
        self.assertEqual(text.count("\n  news:\n"), 1)

    def test_default_config_is_non_publishing(self):
        config = Config.load("config/default.yaml")
        self.assertFalse(config.workflow.checkpoint_enabled)
        self.assertFalse(config.steps.youtube.enabled)
        self.assertTrue(config.steps.youtube.dry_run)
        self.assertEqual(config.steps.youtube.default_visibility, "private")
        self.assertFalse(config.steps.twitter.enabled)
        self.assertTrue(config.steps.twitter.dry_run)
        self.assertFalse(config.steps.linkedin.enabled)
        self.assertFalse(config.steps.hatena.enabled)
        self.assertFalse(config.steps.buzzsprout.publish_immediately)
        self.assertFalse(config.automation.enabled)
        self.assertEqual(config.automation.services, [])
        self.assertEqual(config.automation.schedules, [])

    def test_yaml_parses_to_one_steps_mapping(self):
        raw = yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))
        self.assertIsInstance(raw["steps"]["news"], dict)
        self.assertEqual(raw["steps"]["youtube"]["dry_run"], True)


if __name__ == "__main__":
    unittest.main()
