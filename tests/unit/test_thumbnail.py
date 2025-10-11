import pytest

from src.models import Script, ScriptSegment
from src.steps.thumbnail import ThumbnailGenerator

pytestmark = pytest.mark.unit


class TestThumbnailGeneratorUnit:
    def test_wrap_text_handles_long_japanese(self, tmp_path):
        step = ThumbnailGenerator(run_id="test", run_dir=tmp_path, thumbnail_config={"width": 640, "height": 360})
        lines = step._wrap_text("これは非常に長い日本語のテキストで、適切に改行される必要があります。", max_chars=8)
        assert len(lines) >= 2
        assert all(len(line) <= 8 for line in lines)

    def test_build_callouts_prefers_metadata_keywords(self, tmp_path):
        step = ThumbnailGenerator(run_id="test", run_dir=tmp_path, thumbnail_config={"width": 640, "height": 360})
        script = Script(
            segments=[
                ScriptSegment(speaker="春日部つむぎ", text="金融市場が動いています"),
                ScriptSegment(speaker="ずんだもん", text="円安が進行しています"),
            ]
        )
        metadata = {"tags": ["金融", "経済", "速報"]}

        callouts = step._build_callouts(metadata, script)
        assert callouts[0] == "金融"

    def test_subtitle_text_falls_back_to_speakers(self, tmp_path):
        step = ThumbnailGenerator(run_id="test", run_dir=tmp_path, thumbnail_config={"width": 640, "height": 360})
        script = Script(
            segments=[
                ScriptSegment(speaker="春日部つむぎ", text="こんにちは"),
                ScriptSegment(speaker="ずんだもん", text="解説します"),
            ]
        )

        subtitle = step._build_subtitle_text(None, script)
        assert "春日部つむぎ" in subtitle
        assert "ずんだもん" in subtitle

    def test_execute_requires_script(self, tmp_path):
        step = ThumbnailGenerator(run_id="test", run_dir=tmp_path, thumbnail_config={"width": 640, "height": 360})
        with pytest.raises(ValueError):
            step.execute({})
