from pathlib import Path
import sys

import pytest
import yaml

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.providers.video_effects import VideoEffectPipeline
from src.utils.config import Config


@pytest.mark.unit
def test_config_supports_multi_overlay(tmp_path):
    data = yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))
    data["steps"]["video"]["effects"][1] = {
        "type": "multi_overlay",
        "overlays": [
            {"image_path": "assets/a.png"},
            {"image_path": "assets/b.png", "enabled": False},
            {"image_path": "assets/c.png", "height_ratio": 0.3},
        ],
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    config = Config.load(config_path)
    effect = config.steps.video.effects[1]
    pipeline = VideoEffectPipeline.from_config([effect])
    assert effect.type == "multi_overlay"
    assert len(pipeline.effects[0].overlays) == 2
