import pytest
from pathlib import Path
from src.utils.config import Config


class TestConfig:
    def test_load_default_config(self):
        config = Config.load()
        assert config.workflow.default_run_dir == "runs"
        assert config.workflow.checkpoint_enabled is True

    def test_steps_config(self):
        config = Config.load()
        assert config.steps.news.count == 3
        assert config.steps.script.min_duration == 300
        assert config.steps.audio.sample_rate == 24000
        assert config.steps.video.fps == 25

    def test_providers_config(self):
        config = Config.load()
        assert config.providers.llm.gemini.model == "gemini-1.5-flash"
        assert config.providers.tts.voicevox.enabled is True
        assert config.providers.tts.voicevox.speakers["田中"] == 11

    def test_logging_config(self):
        config = Config.load()
        assert config.logging.level == "INFO"
        assert config.logging.format == "json"
