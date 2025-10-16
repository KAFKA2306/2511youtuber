from datetime import datetime

import pytest

from src.models import NewsItem, ScriptSegment

pytestmark = pytest.mark.unit


class TestScriptSegment:
    def test_valid_segment(self):
        segment = ScriptSegment(speaker="春日部つむぎ", text="こんにちは")
        assert segment.speaker == "春日部つむぎ"
        assert segment.text == "こんにちは"

    def test_accepts_non_japanese_text(self):
        segment = ScriptSegment(speaker="ずんだもん", text="Hello world")
        assert segment.text == "Hello world"

    def test_sentence_break_insertion(self, tmp_path):
        from src.steps.script import ScriptGenerator

        speakers = {
            "analyst": {"name": "田中"},
            "reporter": {"name": "鈴木"},
            "narrator": {"name": "ナレーター"}
        }
        gen = ScriptGenerator("test", tmp_path, speakers_config=speakers)
        raw = '{"segments": [{"speaker": "田中", "text": "今日は晴れです。明日は雨です。"}]}'
        script = gen._parse_and_validate(raw)
        assert script.segments[0].text == "今日は晴れです。\n明日は雨です。"

    def test_sentence_break_preserves_existing(self, tmp_path):
        from src.steps.script import ScriptGenerator

        speakers = {
            "analyst": {"name": "田中"},
            "reporter": {"name": "鈴木"},
            "narrator": {"name": "ナレーター"}
        }
        gen = ScriptGenerator("test", tmp_path, speakers_config=speakers)
        raw = '{"segments": [{"speaker": "田中", "text": "今日は晴れです。\\n明日は雨です。"}]}'
        script = gen._parse_and_validate(raw)
        assert script.segments[0].text == "今日は晴れです。\n明日は雨です。"

    def test_sentence_break_preserves_end_period(self, tmp_path):
        from src.steps.script import ScriptGenerator

        speakers = {
            "analyst": {"name": "田中"},
            "reporter": {"name": "鈴木"},
            "narrator": {"name": "ナレーター"}
        }
        gen = ScriptGenerator("test", tmp_path, speakers_config=speakers)
        raw = '{"segments": [{"speaker": "田中", "text": "今日は晴れです。"}]}'
        script = gen._parse_and_validate(raw)
        assert script.segments[0].text == "今日は晴れです。"


class TestNewsItem:
    def test_create_news_item(self):
        news = NewsItem(title="金融ニュース", summary="テスト要約", url="https://example.com")
        assert news.title == "金融ニュース"
        assert isinstance(news.published_at, datetime)


class TestWorkflowState:
    def test_create_state(self):
        state = WorkflowState(run_id="test_001")
        assert state.run_id == "test_001"
        assert state.status == "running"
        assert len(state.completed_steps) == 0

    def test_mark_completed(self):
        state = WorkflowState(run_id="test_001")
        state.mark_completed("step1", "/path/to/output")
        assert "step1" in state.completed_steps
        assert state.outputs["step1"] == "/path/to/output"

    def test_mark_failed(self):
        state = WorkflowState(run_id="test_001")
        state.mark_failed("Test error")
        assert state.status == "failed"
        assert "Test error" in state.errors
        assert state.completed_at is not None

    def test_mark_success(self):
        state = WorkflowState(run_id="test_001")
        state.mark_success()
        assert state.status == "completed"
        assert state.completed_at is not None
