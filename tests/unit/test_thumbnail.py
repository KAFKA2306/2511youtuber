import pytest

from src.steps.thumbnail import ThumbnailGenerator

pytestmark = pytest.mark.unit


class TestThumbnailGeneratorUnit:
    def test_wrap_text_handles_long_japanese(self, tmp_path):
        step = ThumbnailGenerator(run_id="test", run_dir=tmp_path, thumbnail_config={"width": 640, "height": 360})
        lines = step._wrap_text("これは非常に長い日本語のテキストで、適切に改行される必要があります。", max_chars=8)
        assert len(lines) >= 2
        assert all(len(line) <= 8 for line in lines)
