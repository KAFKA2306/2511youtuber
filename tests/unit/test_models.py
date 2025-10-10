import pytest
from src.models import ScriptSegment, Script, is_pure_japanese, NewsItem, WorkflowState
from pathlib import Path
from datetime import datetime


class TestJapaneseValidation:
    def test_pure_japanese_hiragana(self):
        assert is_pure_japanese("こんにちは")

    def test_pure_japanese_katakana(self):
        assert is_pure_japanese("カタカナ")

    def test_pure_japanese_kanji(self):
        assert is_pure_japanese("日本語")

    def test_pure_japanese_mixed(self):
        assert is_pure_japanese("日本語のテスト文章です。")

    def test_pure_japanese_with_punctuation(self):
        assert is_pure_japanese("こんにちは！今日は良い天気ですね。")

    def test_pure_japanese_with_numbers(self):
        assert is_pure_japanese("2025年10月10日")

    def test_not_pure_japanese_english(self):
        assert not is_pure_japanese("Hello world")

    def test_not_pure_japanese_mixed(self):
        assert not is_pure_japanese("日本語とEnglish")


class TestScriptSegment:
    def test_valid_segment(self):
        segment = ScriptSegment(speaker="田中", text="こんにちは")
        assert segment.speaker == "田中"
        assert segment.text == "こんにちは"

    def test_reject_english_text(self):
        with pytest.raises(ValueError, match="Non-Japanese"):
            ScriptSegment(speaker="田中", text="Hello world")

    def test_reject_mixed_text(self):
        with pytest.raises(ValueError, match="Non-Japanese"):
            ScriptSegment(speaker="鈴木", text="日本語とEnglish")


class TestScript:
    def test_japanese_purity_100(self):
        script = Script(segments=[
            ScriptSegment(speaker="田中", text="こんにちは"),
            ScriptSegment(speaker="鈴木", text="今日は良い天気ですね"),
        ])
        assert script.japanese_purity() == 1.0

    def test_empty_script_purity(self):
        script = Script(segments=[])
        assert script.japanese_purity() == 0.0


class TestNewsItem:
    def test_create_news_item(self):
        news = NewsItem(
            title="金融ニュース",
            summary="テスト要約",
            url="https://example.com"
        )
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
