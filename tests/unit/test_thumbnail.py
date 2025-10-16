import pytest

from src.steps.thumbnail import ThumbnailGenerator

pytestmark = pytest.mark.unit


class TestThumbnailGeneratorUnit:
    def test_wrap_text_handles_long_japanese(self, tmp_path):
        step = ThumbnailGenerator(run_id="test", run_dir=tmp_path, thumbnail_config={"width": 640, "height": 360, "max_chars_per_line": 8})
        font = step._load_font(48)
        lines = step._wrap_text("これは非常に長い日本語のテキストで、適切に改行される必要があります。", font, 400)
        assert len(lines) >= 2
        assert all(len(line) <= 8 for line in lines)
