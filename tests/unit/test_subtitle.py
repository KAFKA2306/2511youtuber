from pathlib import Path

import pytest

from src.steps.subtitle import SubtitleFormatter

pytestmark = pytest.mark.unit


class TestSubtitleFormatter:
    def test_wrap_visual_line_splits_at_period(self):
        formatter = SubtitleFormatter("test", Path("/tmp"), max_chars_per_line=20)
        result = formatter._wrap_visual_line("今日は晴れです。明日は雨です。", 20)
        assert len(result) == 2
        assert result[0] == "今日は晴れです。"
        assert result[1] == "明日は雨です。"

    def test_wrap_visual_line_keeps_short_sentence(self):
        formatter = SubtitleFormatter("test", Path("/tmp"), max_chars_per_line=30)
        result = formatter._wrap_visual_line("今日は晴れです。", 30)
        assert len(result) == 1
        assert result[0] == "今日は晴れです。"


    def test_wrap_visual_line_empty_string(self):
        formatter = SubtitleFormatter("test", Path("/tmp"), max_chars_per_line=20)
        result = formatter._wrap_visual_line("", 20)
        assert result == [""]

    def test_wrap_text_respects_existing_newlines(self):
        formatter = SubtitleFormatter("test", Path("/tmp"), max_chars_per_line=30)
        result = formatter._wrap_text("今日は晴れです。\n明日は雨です。")
        assert len(result) >= 2
