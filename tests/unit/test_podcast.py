from pathlib import Path

import pytest

try:
    from feedgen.feed import FeedGenerator  # noqa: F401

    feedgen_installed = True
except ImportError:
    feedgen_installed = False

@pytest.mark.unit
@pytest.mark.skipif(not feedgen_installed, reason="feedgen is not installed")
def test_podcast_exporter_creates_feed(tmp_path: Path) -> None:
    from src.steps.podcast import PodcastExporter

    run_id = "test-run"
    run_dir = tmp_path
    audio_path = tmp_path / "input.wav"
    audio_path.write_bytes(b"fake wav data")

    exporter = PodcastExporter(run_id=run_id, run_dir=run_dir)
    output_path = exporter.execute({"synthesize_audio": audio_path})

    expected_dir = run_dir / run_id
    assert output_path == expected_dir / "podcast.xml"
    assert output_path.exists()
    assert (expected_dir / "podcast_audio.wav").exists()

    feed_content = output_path.read_text(encoding="utf-8")
    assert "Episode test-run" in feed_content
    assert "金融ニュース解説ポッドキャスト" in feed_content

