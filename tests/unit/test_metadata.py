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
