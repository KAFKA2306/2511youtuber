from datetime import datetime

import pytest

from src.models import NewsItem, ScriptSegment, WorkflowState

pytestmark = pytest.mark.unit


class TestScriptSegment:
    def test_valid_segment(self):
        segment = ScriptSegment(speaker="春日部つむぎ", text="こんにちは")
        assert segment.speaker == "春日部つむぎ"
        assert segment.text == "こんにちは"

    def test_accepts_non_japanese_text(self):
        segment = ScriptSegment(speaker="ずんだもん", text="Hello world")
        assert segment.text == "Hello world"


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
