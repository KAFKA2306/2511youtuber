"""
Complete E2E test with video rendering - validates entire pipeline including FFmpeg.
This test is slow (~5-10 minutes) but validates the full production workflow.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.media_utils import get_audio_duration
from src.core.orchestrator import WorkflowOrchestrator
from src.steps.audio import AudioSynthesizer
from src.steps.news import NewsCollector
from src.steps.script import ScriptGenerator
from src.steps.subtitle import SubtitleFormatter
from src.steps.video import VideoRenderer
from src.utils.config import Config


def assert_valid_file(path: Path, min_size_kb: float = 0.1) -> None:
    """Assert file exists and has content."""
    assert path.exists(), f"Missing: {path}"
    size_kb = path.stat().st_size / 1024
    assert size_kb >= min_size_kb, f"Too small: {path.name} = {size_kb:.2f}KB < {min_size_kb}KB"


@pytest.mark.slow
def test_full_workflow_with_video_rendering(tmp_path: Path) -> None:
    """
    Complete end-to-end workflow including FFmpeg video rendering.

    This is the ULTIMATE validation test:
    - Real Gemini API for news and script
    - Real Voicevox for audio synthesis
    - Real FFmpeg for video rendering
    - Validates actual production-ready video output

    Expected runtime: 5-10 minutes
    """
    run_id = "test_full_e2e"
    config = Config.load()

    steps = [
        NewsCollector(run_id, tmp_path, **config.steps.news.model_dump(), providers_config=config.providers.news),
        ScriptGenerator(run_id, tmp_path, config.steps.script.model_dump()),
        AudioSynthesizer(run_id, tmp_path, config.providers.tts.voicevox.model_dump()),
        SubtitleFormatter(run_id, tmp_path),
        VideoRenderer(run_id, tmp_path, config.steps.video.model_dump()),
    ]

    print("\n🎬 Starting full E2E workflow (this will take several minutes)...")

    orchestrator = WorkflowOrchestrator(run_id, steps, tmp_path)
    result = orchestrator.execute()

    assert result.status == "success", f"Full workflow failed: {result.errors}"
    assert len(result.outputs) == 5, f"Expected 5 outputs, got {len(result.outputs)}"

    run_dir = tmp_path / run_id

    # Validate all intermediate outputs
    news_path = run_dir / "news.json"
    assert_valid_file(news_path, min_size_kb=1)
    news = json.loads(news_path.read_text(encoding="utf-8"))
    assert isinstance(news, list), "News should be a list"
    assert len(news) > 0, "Must have news articles"

    script_path = run_dir / "script.json"
    assert_valid_file(script_path, min_size_kb=1)
    script = json.loads(script_path.read_text(encoding="utf-8"))
    assert len(script["segments"]) > 0, "Must have script segments"

    audio_path = run_dir / "audio.wav"
    assert_valid_file(audio_path, min_size_kb=50)
    audio_duration = get_audio_duration(audio_path)
    assert audio_duration > 5, f"Audio too short: {audio_duration}s"

    subtitle_path = run_dir / "subtitles.srt"
    assert_valid_file(subtitle_path)

    # THE CRITICAL VALIDATION: Video file
    video_path = run_dir / "video.mp4"
    assert_valid_file(video_path, min_size_kb=500)

    video_duration = get_audio_duration(video_path)
    assert abs(video_duration - audio_duration) < 2.0, (
        f"Video/audio duration mismatch: {video_duration:.1f}s vs {audio_duration:.1f}s"
    )

    print("✅ FULL E2E TEST PASSED")
    print(f"   Video: {video_path}")
    print(f"   Duration: {video_duration:.1f}s")
    print(f"   Size: {video_path.stat().st_size / (1024 * 1024):.1f}MB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
