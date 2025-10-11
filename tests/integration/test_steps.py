import json
import shutil
from pathlib import Path

import pytest

from PIL import Image
from src.models import NewsItem, Script
from src.steps.audio import AudioSynthesizer
from src.steps.metadata import MetadataAnalyzer
from src.steps.news import NewsCollector
from src.steps.script import ScriptGenerator
from src.steps.subtitle import SubtitleFormatter
from src.steps.thumbnail import ThumbnailGenerator
from src.steps.youtube import YouTubeUploader
from src.utils.config import Config


@pytest.mark.integration
@pytest.mark.skipif(
    not Path.home().joinpath(".secrets/PERPLEXITY_API_KEY").exists(), reason="Requires PERPLEXITY_API_KEY"
)
class TestNewsCollectorIntegration:
    def test_news_collection_creates_valid_output(self, temp_run_dir, test_run_id):
        from src.utils.config import Config

        config = Config.load()
        step = NewsCollector(run_id=test_run_id, run_dir=temp_run_dir, count=2, providers_config=config.providers.news)
        output_path = step.run({})

        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 2
        for item in data:
            news_item = NewsItem(**item)
            assert news_item.title
            assert news_item.summary


@pytest.mark.integration
class TestScriptGeneratorIntegration:
    def test_script_generation_with_dummy_llm(self, temp_run_dir, test_run_id, sample_news_path):
        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)
        news_output_path = run_path / "news.json"
        shutil.copy(sample_news_path, news_output_path)

        speakers = Config.load().steps.script.speakers
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir, speakers_config=speakers)
        output_path = step.run({"collect_news": news_output_path})

        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        script = Script(**data)
        assert len(script.segments) >= 3

    def test_script_recursive_yaml_parsing(self, temp_run_dir, test_run_id):
        speakers = Config.load().steps.script.speakers
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir, speakers_config=speakers)

        nested_yaml = """
        "segments:
          - speaker: 春日部つむぎ
            text: こんにちは"
        """

        script = step._parse_and_validate(nested_yaml)
        assert len(script.segments) == 1
        assert script.segments[0].speaker == "春日部つむぎ"


@pytest.mark.integration
class TestAudioSynthesizerIntegration:
    def test_audio_synthesis_with_pyttsx3(self, temp_run_dir, test_run_id, sample_script_path):
        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)
        script_output_path = run_path / "script.json"
        shutil.copy(sample_script_path, script_output_path)

        step = AudioSynthesizer(
            run_id=test_run_id,
            run_dir=temp_run_dir,
            pyttsx3_config={
                "speakers": {"春日部つむぎ": {"rate": 140}, "ずんだもん": {"rate": 160}, "玄野武宏": {"rate": 150}}
            },
        )
        output_path = step.run({"generate_script": script_output_path})

        assert output_path.exists()
        assert output_path.stat().st_size > 0


@pytest.mark.integration
class TestSubtitleFormatterIntegration:
    def test_subtitle_generation(self, temp_run_dir, test_run_id, sample_script_path):
        from pydub.generators import Sine

        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)

        script_output_path = run_path / "script.json"
        shutil.copy(sample_script_path, script_output_path)

        audio_path = run_path / "audio.wav"
        dummy_audio = Sine(440).to_audio_segment(duration=5000)
        dummy_audio.export(audio_path, format="wav")

        step = SubtitleFormatter(run_id=test_run_id, run_dir=temp_run_dir, max_chars_per_line=24)
        output_path = step.run({"generate_script": script_output_path, "synthesize_audio": audio_path})

        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            content = f.read()

        assert "1" in content
        assert "-->" in content
        assert "こんにちは" in content

    def test_timestamp_calculation(self, temp_run_dir, test_run_id):
        step = SubtitleFormatter(run_id=test_run_id, run_dir=temp_run_dir, max_chars_per_line=24)

        from src.models import Script, ScriptSegment

        script = Script(
            segments=[
                ScriptSegment(speaker="春日部つむぎ", text="短い"),
                ScriptSegment(speaker="ずんだもん", text="これは長いテキストです。"),
            ]
        )

        timestamps = step._calculate_timestamps(script, 10.0)

        assert len(timestamps) == 2
        assert timestamps[0]["start"] == 0.0
        assert timestamps[1]["end"] == 10.0
        assert timestamps[0]["end"] < timestamps[1]["start"]

    def test_wraps_long_lines(self, temp_run_dir, test_run_id, sample_script_path):
        from pydub.generators import Sine

        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)

        script_output_path = run_path / "script.json"
        shutil.copy(sample_script_path, script_output_path)

        audio_path = run_path / "audio.wav"
        dummy_audio = Sine(440).to_audio_segment(duration=5000)
        dummy_audio.export(audio_path, format="wav")

        step = SubtitleFormatter(
            run_id=test_run_id,
            run_dir=temp_run_dir,
            max_chars_per_line=10,
        )
        output_path = step.run({"generate_script": script_output_path, "synthesize_audio": audio_path})

        import unicodedata

        def visual_width(value: str) -> int:
            width = 0
            for ch in value:
                if unicodedata.east_asian_width(ch) in ("F", "W"):
                    width += 2
                else:
                    width += 1
            return width

        with open(output_path, encoding="utf-8") as f:
            for line in f:
                text_line = line.strip()
                if not text_line or text_line.isdigit() or "-->" in text_line:
                    continue
                assert visual_width(text_line) <= 10


@pytest.mark.integration
class TestMetadataAnalyzerIntegration:
    def test_metadata_analysis_produces_recommendations(self, temp_run_dir, test_run_id, sample_script_path):
        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)

        script_output_path = run_path / "script.json"
        shutil.copy(sample_script_path, script_output_path)

        step = MetadataAnalyzer(
            run_id=test_run_id,
            run_dir=temp_run_dir,
            metadata_config={
                "target_keywords": ["金融", "経済"],
                "min_keyword_density": 0.02,
                "max_title_length": 60,
                "max_description_length": 500,
                "default_tags": ["金融ニュース"],
            },
        )

        output_path = step.run({"generate_script": script_output_path})

        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            metadata = json.load(f)

        assert "title" in metadata
        assert "recommendations" in metadata
        assert metadata["tags"]


@pytest.mark.integration
class TestThumbnailGeneratorIntegration:
    def test_thumbnail_generation(self, temp_run_dir, test_run_id, sample_script_path, sample_metadata_path):
        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)

        script_output_path = run_path / "script.json"
        shutil.copy(sample_script_path, script_output_path)

        metadata_path = run_path / "metadata.json"
        shutil.copy(sample_metadata_path, metadata_path)

        step = ThumbnailGenerator(
            run_id=test_run_id,
            run_dir=temp_run_dir,
            thumbnail_config={
                "width": 640,
                "height": 360,
                "background_color": "#1a2238",
                "title_color": "#FFFFFF",
                "subtitle_color": "#FFD166",
                "accent_color": "#EF476F",
                "padding": 48,
                "max_lines": 3,
                "max_chars_per_line": 10,
                "title_font_size": 64,
                "subtitle_font_size": 36,
            },
        )

        output_path = step.run(
            {
                "generate_script": script_output_path,
                "analyze_metadata": metadata_path,
            }
        )

        assert output_path.exists()

        with Image.open(output_path) as img:
            assert img.size == (640, 360)


@pytest.mark.integration
class TestYouTubeUploaderIntegration:
    def test_youtube_uploader_dry_run(self, temp_run_dir, test_run_id):
        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)

        video_path = run_path / "video.mp4"
        video_path.write_bytes(b"dummy video")

        metadata_path = run_path / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "title": "テスト動画",
                    "description": "説明",
                    "tags": ["テスト"],
                },
                f,
            )

        step = YouTubeUploader(
            run_id=test_run_id,
            run_dir=temp_run_dir,
            youtube_config={
                "dry_run": True,
                "default_visibility": "unlisted",
                "category_id": 24,
                "default_tags": ["金融"],
            },
        )

        output_path = step.run(
            {
                "render_video": video_path,
                "analyze_metadata": metadata_path,
            }
        )

        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            payload = json.load(f)
        assert payload["status"] == "dry_run"
