import json

import pytest

from src.steps.metadata import MetadataAnalyzer

pytestmark = pytest.mark.unit


class TestMetadataAnalyzerUnit:
    def _make_step(self, temp_run_dir, test_run_id):
        return MetadataAnalyzer(
            run_id=test_run_id,
            run_dir=temp_run_dir,
            metadata_config={"use_llm": False},
        )

    def test_parse_llm_response_handles_triple_quotes(self, temp_run_dir, test_run_id):
        step = self._make_step(temp_run_dir, test_run_id)

        raw = (
            "了解しました。\n" \
            "'''\n" \
            "title: \"テスト\"\n" \
            "title_alt1: \"代替\"\n" \
            "description: |\n  本文\n" \
            "tags:\n  - a\n  - b\n" \
            "category_id: 25\n" \
            "'''"
        )

        metadata = step._parse_llm_response(raw)

        assert metadata["title"] == "テスト"
        assert metadata["tags"] == ["a", "b"]

    def test_parse_llm_response_handles_code_block_with_preamble(self, temp_run_dir, test_run_id):
        step = self._make_step(temp_run_dir, test_run_id)

        raw = (
            "はい。\n" \
            "```yaml\n" \
            "title: \"foo\"\n" \
            "description: bar\n" \
            "tags:\n  - baz\n" \
            "category_id: 25\n" \
            "```"
        )

        metadata = step._parse_llm_response(raw)

        assert metadata["title"] == "foo"
        assert metadata["category_id"] == 25

    def test_execute_falls_back_when_llm_metadata_invalid(self, temp_run_dir, test_run_id):
        run_path = temp_run_dir / test_run_id
        run_path.mkdir()

        script_path = run_path / "script.json"
        script_payload = {
            "segments": [
                {"speaker": "ナレーター", "text": "金融市場最新動向"},
                {"speaker": "解説", "text": "株価は乱高下しています"},
            ],
            "total_duration_estimate": 120.0,
        }
        script_path.write_text(json.dumps(script_payload, ensure_ascii=False), encoding="utf-8")

        step = MetadataAnalyzer(
            run_id=test_run_id,
            run_dir=temp_run_dir,
            metadata_config={"use_llm": False},
        )

        class DummyProvider:
            def is_available(self):
                return True

            def execute(self, prompt):
                return "nonsense"

        step.use_llm = True
        step.llm_provider = DummyProvider()

        output_path = step.execute({"generate_script": script_path})

        result = json.loads(output_path.read_text(encoding="utf-8"))

        assert result["title"] == "金融市場最新動向｜金融ニュース"
        assert result["tags"] == ["金融", "株価", "市場"]
        assert result["category_id"] == 25

    def test_normalize_tags_handles_string_payload(self, temp_run_dir, test_run_id):
        step = self._make_step(temp_run_dir, test_run_id)

        tags = step._normalize_tags("金融, 株価 , , 投資")

        assert tags == ["金融", "株価", "投資"]
