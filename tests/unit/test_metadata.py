import json

import pytest

from src.steps.metadata import MetadataAnalyzer

pytestmark = pytest.mark.unit


class TestMetadataAnalyzerUnit:
    def test_metadata_generation(self, temp_run_dir, test_run_id, sample_script_path):
        import shutil

        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)

        script_output_path = run_path / "script.json"
        shutil.copy(sample_script_path, script_output_path)

        analyzer = MetadataAnalyzer(
            run_id=test_run_id,
            run_dir=temp_run_dir,
            metadata_config={
                "target_keywords": ["金融", "経済"],
                "max_title_length": 50,
                "max_description_length": 400,
                "default_tags": ["金融ニュース"],
                "use_llm": False,
            },
        )

        output_path = analyzer.run({"generate_script": script_output_path})

        with open(output_path, encoding="utf-8") as f:
            metadata = json.load(f)

        assert metadata["tags"][0] == "金融ニュース"
        assert metadata["analysis"]["segments"] > 0
        assert metadata["recommendations"] == []
