from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.utils.config import Config
from src.utils.secrets import load_secret_values


def test_config_load_round_trip(tmp_path: Path) -> None:
    config_data = {
        "workflow": {"default_run_dir": "runs", "checkpoint_enabled": True},
        "steps": {
            "news": {"count": 5, "query": "日本の金融"},
            "script": {
                "min_duration": 120,
                "max_duration": 360,
                "target_wow_score": 0.85,
                "speakers": {
                    "analyst": {"name": "Analyst", "aliases": ["A"]},
                    "reporter": {"name": "Reporter", "aliases": ["R"]},
                    "narrator": {"name": "Narrator", "aliases": []},
                },
            },
            "audio": {"sample_rate": 48000, "format": "wav"},
            "subtitle": {
                "width_per_char_pixels": 48,
                "min_visual_width": 480,
                "max_visual_width": 960,
            },
            "video": {
                "resolution": "1920x1080",
                "fps": 30,
                "codec": "h264",
                "preset": "medium",
                "crf": 18,
                "effects": [
                    {
                        "type": "ken_burns",
                        "enabled": True,
                        "zoom_speed": 0.002,
                        "max_zoom": 1.15,
                        "hold_frame_factor": 1.5,
                        "pan_mode": "left_to_right",
                    },
                    {
                        "type": "tsumugi_overlay",
                        "enabled": True,
                        "offset": {"right": 24, "bottom": 12},
                    },
                ],
                "subtitles": {"font_name": "Noto Sans", "font_size": 48},
            },
            "thumbnail": {
                "enabled": True,
                "width": 1280,
                "height": 720,
                "background_color": "#ffffff",
                "title_color": "#111111",
                "subtitle_color": "#333333",
                "overlays": [
                    {
                        "name": "badge",
                        "enabled": True,
                        "image_path": "assets/badge.png",
                        "anchor": "top_left",
                        "width_ratio": 0.25,
                    }
                ],
            },
            "metadata": {
                "enabled": True,
                "use_llm": True,
                "llm_model": "gemini/gemini-2.0-flash-exp",
                "fallback_llm_model": "gemini/gemini-pro",
                "llm_temperature": 0.4,
                "llm_max_tokens": 1024,
                "target_keywords": ["日経平均", "株価"],
                "max_title_length": 60,
                "max_description_length": 300,
                "default_tags": ["finance", "jp"],
            },
            "youtube": {
                "enabled": True,
                "dry_run": True,
                "default_visibility": "private",
                "category_id": 27,
                "default_tags": ["automation"],
            },
            "twitter": {
                "enabled": True,
                "dry_run": True,
                "clip_duration_seconds": 45,
                "start_offset_seconds": 1.5,
                "thumbnail_path": "assets/thumb.png",
            },
            "podcast": {
                "enabled": True,
                "feed_title": "Finance podcast",
                "feed_description": "Daily market update",
                "feed_author": "AI Host",
                "feed_url": "https://example.com/podcast",
            },
            "buzzsprout": {
                "enabled": True,
                "podcast_id": "12345",
                "title_template": "Episode {run_id}",
                "publish_immediately": False,
            },
        },
        "providers": {
            "llm": {
                "gemini": {
                    "model": "gemini/gemini-2.0-flash-exp",
                    "fallback_model": "gemini/gemini-pro",
                    "temperature": 0.5,
                    "max_tokens": 2048,
                }
            },
            "tts": {
                "voicevox": {
                    "enabled": True,
                    "url": "http://localhost:50021",
                    "speakers": {"tsumugi": 3},
                    "auto_start": True,
                }
            },
            "news": {
                "perplexity": {
                    "enabled": True,
                    "model": "sonar",
                    "temperature": 0.1,
                    "max_tokens": 1536,
                    "search_recency_filter": "week",
                }
            },
        },
        "logging": {"level": "INFO", "format": "%(message)s"},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")

    config = Config.load(config_path)

    assert config.workflow.default_run_dir == "runs"
    assert config.steps.video.effects[0].type == "ken_burns"
    assert config.steps.video.effects[1].offset.right == 24
    assert config.providers.llm.gemini.fallback_model == "gemini/gemini-pro"
    assert config.steps.thumbnail.overlays[0].width_ratio == 0.25


def test_load_secret_values_merges_env_and_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "env-value")
    monkeypatch.setenv("GEMINI_API_KEY_2", "env-second")

    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY= file-value\nGEMINI_API_KEY_3=third\n", encoding="utf-8")

    values = load_secret_values("gemini_api_key", extra_dirs=[tmp_path])

    assert values[0] == "env-value"
    assert "env-second" in values
    assert "third" in values
    assert "file-value" in values
    assert len(values) == len(set(values))
