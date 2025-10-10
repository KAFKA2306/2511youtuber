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
        assert config.steps.subtitle.width_per_char_pixels == 70
        assert config.steps.subtitle.min_visual_width == 16
        assert config.steps.subtitle.max_visual_width == 40
        assert config.steps.video.fps == 25
        assert config.steps.video.effects[0].type == "ken_burns"
        assert config.steps.thumbnail.enabled is True
        assert config.steps.thumbnail.width == 1280
        assert config.steps.metadata.min_keyword_density == 0.01
        assert config.steps.youtube.enabled is True

    def test_providers_config(self):
        config = Config.load()
        assert config.providers.llm.gemini.model == "gemini/gemini-2.5-flash-preview-09-2025"
        assert config.providers.tts.voicevox.enabled is True
        assert config.providers.tts.voicevox.speakers["田中"] == 11
        assert config.providers.tts.voicevox.manager_script == "scripts/voicevox_manager.sh"
        assert config.providers.tts.voicevox.auto_start is True
        assert config.providers.tts.voicevox.query_timeout == 10
        assert config.providers.tts.voicevox.synthesis_timeout == 30
        assert config.providers.tts.voicevox.startup_timeout_seconds == 60
        assert config.providers.tts.voicevox.startup_poll_interval_seconds == 2

    def test_logging_config(self):
        config = Config.load()
        assert config.logging.level == "INFO"
        assert config.logging.format == "json"
