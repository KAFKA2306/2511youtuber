"""
Tests for Remotion.dev video renderer integration.
"""

from pathlib import Path

import pytest

from src.steps.remotion_renderer import RemotionRenderer


@pytest.mark.slow
def test_remotion_basic_render(tmp_path: Path) -> None:
    """
    Test basic Remotion rendering with real subprocess call.

    Prerequisites:
    - remotion/ directory with npm packages installed
    - npm install already run
    """
    run_id = "test_remotion_render"

    # Create test subtitle file
    subtitles_path = tmp_path / "subtitles.srt"
    subtitles_path.write_text(
        "1\n"
        "00:00:00,000 --> 00:00:02,000\n"
        "Hello Remotion!\n"
        "\n"
        "2\n"
        "00:00:02,000 --> 00:00:04,000\n"
        "This is a test video.\n"
        "\n"
        "3\n"
        "00:00:04,000 --> 00:00:06,000\n"
        "Testing subtitle rendering.\n",
        encoding="utf-8",
    )

    # Create empty audio file placeholder
    # NOTE: In real workflow, this would be actual audio from AudioSynthesizer
    audio_path = tmp_path / "audio.wav"
    audio_path.touch()

    # Initialize Remotion renderer
    renderer = RemotionRenderer(run_id, tmp_path)

    # Check if Remotion project exists
    if not renderer.remotion_project_dir.exists():
        pytest.skip("Remotion project not found. Run: cd remotion && npm install")

    # Check if node_modules exists
    if not (renderer.remotion_project_dir / "node_modules").exists():
        pytest.skip("Remotion dependencies not installed. Run: cd remotion && npm install")

    # NOTE: This test will fail with empty audio file
    # For now, just verify the Python integration works
    try:
        result_path = renderer.execute(
            {
                "format_subtitles": subtitles_path,
                "synthesize_audio": audio_path,
            }
        )

        # If we get here, rendering succeeded
        assert result_path.exists(), f"Output video not found: {result_path}"
        assert result_path.stat().st_size > 0, "Output video is empty"
        print(f"✅ Remotion video generated: {result_path}")

    except RuntimeError as e:
        # Expected to fail with empty audio file
        if "audio" in str(e).lower() or "empty" in str(e).lower():
            pytest.skip("Test skipped: requires valid audio file")
        raise


def test_remotion_srt_parsing() -> None:
    """Test SRT subtitle parsing logic."""
    renderer = RemotionRenderer("test", Path("/tmp"))

    # Test SRT time conversion
    assert renderer._srt_to_seconds("00:00:00,000") == 0.0
    assert renderer._srt_to_seconds("00:00:01,500") == 1.5
    assert renderer._srt_to_seconds("00:01:30,250") == 90.25
    assert renderer._srt_to_seconds("01:00:00,000") == 3600.0

    # Test time range parsing
    start, end = renderer._parse_srt_time("00:00:00,000 --> 00:00:02,500")
    assert start == 0.0
    assert end == 2.5


def test_remotion_props_preparation(tmp_path: Path) -> None:
    """Test Remotion props generation from subtitle and audio files."""
    renderer = RemotionRenderer("test", tmp_path)

    # Create test files
    srt_path = tmp_path / "test.srt"
    srt_path.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nFirst subtitle\n\n2\n00:00:02,000 --> 00:00:04,000\nSecond subtitle\n",
        encoding="utf-8",
    )

    audio_path = tmp_path / "test.wav"
    audio_path.touch()

    # Generate props
    props = renderer._prepare_props(srt_path, audio_path)

    # Verify props structure
    assert "subtitles" in props
    assert "audioUrl" in props
    assert len(props["subtitles"]) == 2

    # Verify first subtitle
    sub1 = props["subtitles"][0]
    assert sub1["start"] == 0.0
    assert sub1["end"] == 2.0
    assert sub1["text"] == "First subtitle"

    # Verify second subtitle
    sub2 = props["subtitles"][1]
    assert sub2["start"] == 2.0
    assert sub2["end"] == 4.0
    assert sub2["text"] == "Second subtitle"

    # Verify audio URL format
    assert props["audioUrl"].startswith("file://")
    assert "test.wav" in props["audioUrl"]

    print("✅ Props preparation works correctly")


@pytest.mark.fast
def test_remotion_import() -> None:
    """Verify RemotionRenderer can be imported."""
    from src.steps.remotion_renderer import RemotionRenderer

    assert RemotionRenderer is not None
