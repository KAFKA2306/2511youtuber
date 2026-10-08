import unittest
from pathlib import Path

import yaml


class BusinessEventSchemaTests(unittest.TestCase):
    def test_cta_schema_separates_synthetic_from_actual_observations(self):
        schema = yaml.safe_load(
            Path("config/business_events.yaml").read_text(encoding="utf-8")
        )

        self.assertEqual(schema["schema_version"], 1)
        self.assertTrue(
            {
                "service_page_view",
                "demo_cta_started",
                "poc_cta_started",
            }.issubset(schema["event_types"])
        )
        self.assertEqual(set(schema["observation_kinds"]), {"synthetic", "actual"})
        self.assertTrue(schema["rules"]["actual_requires_provenance"])
        self.assertFalse(schema["rules"]["synthetic_counts_as_business_outcome"])
        self.assertEqual(schema["rules"]["unobserved_outcome"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
