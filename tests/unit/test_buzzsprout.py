from pathlib import Path

import pytest

from src.steps.buzzsprout import BuzzsproutUploader
from src.utils.config import BuzzsproutStepConfig


@pytest.mark.unit
def test_buzzsprout_uploader_posts_audio(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"RIFF")

    monkeypatch.setenv("BUZZSPROUT_API_TOKEN", "token-value")
    monkeypatch.setenv("BUZZSPROUT_PODCAST_ID", "42")

    captured: dict[str, object] = {}

    class DummyResponse:
        status_code = 201

        @staticmethod
        def json() -> dict[str, object]:
            return {"id": 1, "audio_url": "https://example.com"}

    def fake_post(url, headers, data, files, timeout):
        captured.update({"url": url, "headers": headers, "data": data, "filename": files["audio_file"][0]})
        return DummyResponse()

    monkeypatch.setattr("src.steps.buzzsprout.requests.post", fake_post)

    step = BuzzsproutUploader("run-1", tmp_path, BuzzsproutStepConfig(enabled=True))
    output = step.execute({"synthesize_audio": audio_path})

    assert captured["url"] == "https://www.buzzsprout.com/api/42/episodes.json"
    assert captured["headers"]["Authorization"] == "Token token=token-value"
    assert captured["data"]["title"].startswith("金融ニュース解説 Episode run-1")
    assert captured["filename"] == "sample.wav"
    assert output.exists()
