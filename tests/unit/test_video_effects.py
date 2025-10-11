from unittest.mock import MagicMock

import pytest

from src.providers.video_effects import (
    KenBurnsEffect,
    VideoEffectContext,
    VideoEffectPipeline,
)

pytestmark = pytest.mark.unit


class TestVideoEffectPipeline:
    def test_ken_burns_effect_applies_zoom_and_pan(self):
        stream = MagicMock()
        stream.filter.return_value = stream

        pipeline = VideoEffectPipeline.from_config(
            [
                {
                    "type": "ken_burns",
                    "zoom_speed": 0.01,
                    "max_zoom": 1.3,
                    "hold_frame_factor": 0.5,
                    "pan_mode": "left_to_right",
                }
            ]
        )

        context = VideoEffectContext(duration_seconds=12.0, fps=24, resolution=(1280, 720))
        pipeline.apply(stream, context)

        assert stream.filter.call_count == 1
        call = stream.filter.call_args
        assert call.args[0] == "zoompan"
        assert call.kwargs["z"] == "min(zoom+0.01,1.3)"
        assert call.kwargs["d"] == 1
        assert call.kwargs["s"] == "1280x720"
        assert "min(on/287,1)" in call.kwargs["x"]
        assert "ih/2 - (ih/zoom/2)" == call.kwargs["y"]

    def test_disabled_effects_are_skipped(self):
        pipeline = VideoEffectPipeline.from_config([{"type": "ken_burns", "enabled": False}])
        assert pipeline.effects == []

    def test_unknown_effect_raises(self):
        with pytest.raises(ValueError):
            VideoEffectPipeline.from_config([{"type": "unknown"}])


class TestKenBurnsEffect:
    def test_pan_modes_default_to_center(self):
        effect = KenBurnsEffect()
        stream = MagicMock()
        stream.filter.return_value = stream
        context = VideoEffectContext(duration_seconds=5.0, fps=30, resolution=(1920, 1080))

        effect.apply(stream, context)

        call = stream.filter.call_args
        assert call.kwargs["x"] == "iw/2 - (iw/zoom/2)"
        assert call.kwargs["y"] == "ih/2 - (ih/zoom/2)"
