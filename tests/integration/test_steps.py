import pytest
from pathlib import Path
import json
from src.steps.news import NewsCollector
from src.steps.script import ScriptGenerator
from src.steps.audio import AudioSynthesizer
from src.steps.subtitle import SubtitleFormatter
from src.steps.metadata import MetadataAnalyzer
from src.steps.youtube import YouTubeUploader
from src.models import NewsItem, Script


@pytest.mark.integration
class TestNewsCollectorIntegration:
    def test_news_collection_creates_valid_output(self, temp_run_dir, test_run_id):
        step = NewsCollector(run_id=test_run_id, run_dir=temp_run_dir, count=2)
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
        import shutil
        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)
        news_output_path = run_path / "news.json"
        shutil.copy(sample_news_path, news_output_path)

        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir)
        output_path = step.run({"collect_news": news_output_path})

        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        script = Script(**data)
        assert len(script.segments) >= 3
        assert script.japanese_purity() >= 0.95

    def test_script_recursive_yaml_parsing(self, temp_run_dir, test_run_id):
        step = ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir)

        nested_yaml = '''
        "segments:
          - speaker: 田中
            text: こんにちは"
        '''

        script = step._parse_and_validate(nested_yaml)
        assert len(script.segments) == 1
        assert script.segments[0].speaker == "田中"


@pytest.mark.integration
class TestAudioSynthesizerIntegration:
    def test_audio_synthesis_with_pyttsx3(self, temp_run_dir, test_run_id, sample_script_path):
        import shutil
        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)
        script_output_path = run_path / "script.json"
        shutil.copy(sample_script_path, script_output_path)

        step = AudioSynthesizer(
            run_id=test_run_id,
            run_dir=temp_run_dir,
            pyttsx3_config={"speakers": {
                "田中": {"rate": 140},
                "鈴木": {"rate": 160},
                "ナレーター": {"rate": 150}
            }}
        )
        output_path = step.run({"generate_script": script_output_path})

        assert output_path.exists()
        assert output_path.stat().st_size > 0


@pytest.mark.integration
class TestSubtitleFormatterIntegration:
    def test_subtitle_generation(self, temp_run_dir, test_run_id, sample_script_path):
        import shutil
        from pydub import AudioSegment
        from pydub.generators import Sine

        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)

        script_output_path = run_path / "script.json"
        shutil.copy(sample_script_path, script_output_path)

        audio_path = run_path / "audio.wav"
        dummy_audio = Sine(440).to_audio_segment(duration=5000)
        dummy_audio.export(audio_path, format="wav")

        step = SubtitleFormatter(run_id=test_run_id, run_dir=temp_run_dir)
        output_path = step.run({
            "generate_script": script_output_path,
            "synthesize_audio": audio_path
        })

        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            content = f.read()

        assert "1" in content
        assert "-->" in content
        assert "こんにちは" in content

    def test_timestamp_calculation(self, temp_run_dir, test_run_id):
        step = SubtitleFormatter(run_id=test_run_id, run_dir=temp_run_dir)

        from src.models import Script, ScriptSegment
        script = Script(segments=[
            ScriptSegment(speaker="田中", text="短い"),
            ScriptSegment(speaker="鈴木", text="これは長いテキストです。")
        ])

        timestamps = step._calculate_timestamps(script, 10.0)

        assert len(timestamps) == 2
        assert timestamps[0]["start"] == 0.0
        assert timestamps[1]["end"] == 10.0
        assert timestamps[0]["end"] < timestamps[1]["start"]


@pytest.mark.integration
class TestMetadataAnalyzerIntegration:
    def test_metadata_analysis_produces_recommendations(self, temp_run_dir, test_run_id, sample_script_path):
        import shutil

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
class TestYouTubeUploaderIntegration:
    def test_youtube_uploader_dry_run(self, temp_run_dir, test_run_id):
        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)

        video_path = run_path / "video.mp4"
        video_path.write_bytes(b"dummy video")

        metadata_path = run_path / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump({
                "title": "テスト動画",
                "description": "説明",
                "tags": ["テスト"],
            }, f)

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

        output_path = step.run({
            "render_video": video_path,
            "analyze_metadata": metadata_path,
        })

        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["status"] == "dry_run"
        assert data["metadata"]["visibility"] == "unlisted"
