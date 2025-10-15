from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.providers.video_effects import (
    TSUMUGI_OVERLAY_PATH,
    KenBurnsEffect,
    OverlayEffect,
    TsumugiOverlayEffect,
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
        with pytest.raises(KeyError):
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


class TestOverlayEffect:
    @patch("ffmpeg.probe")
    @patch("ffmpeg.input")
    def test_overlay_effect_applies_correctly(self, mock_input, mock_probe):
        # Arrange
        mock_overlay_stream = MagicMock()
        mock_input.return_value = mock_overlay_stream
        mock_overlay_stream.filter.return_value = mock_overlay_stream
        mock_probe.return_value = {"streams": [{"width": 200, "height": 150}]}

        effect = OverlayEffect(
            image_path="dummy.png",
            anchor="bottom_left",
            height_ratio=0.5,
            offset={"left": 10, "bottom": 20},
        )
        main_stream = MagicMock()
        context = VideoEffectContext(duration_seconds=10.0, fps=30, resolution=(1920, 1080))

        # Act
        result_stream = effect.apply(main_stream, context)

        # Assert
        mock_input.assert_called_once_with("dummy.png")
        mock_overlay_stream.filter.assert_called_once_with("scale", 720, 540)
        mock_probe.assert_called_once_with("dummy.png")
        main_stream.overlay.assert_called_once()
        call_args = main_stream.overlay.call_args
        assert call_args.args[0] == mock_overlay_stream
        assert call_args.kwargs["x"] == 10
        assert call_args.kwargs["y"] == 520
        assert result_stream == main_stream.overlay.return_value


class TestTsumugiOverlayEffect:
    @patch("ffmpeg.probe")
    @patch("ffmpeg.input")
    def test_pipeline_includes_default_tsumugi_overlay(self, mock_input, mock_probe):
        mock_overlay_stream = MagicMock()
        mock_input.return_value = mock_overlay_stream
        mock_overlay_stream.filter.return_value = mock_overlay_stream
        mock_probe.return_value = {"streams": [{"width": 400, "height": 800}]}

        pipeline = VideoEffectPipeline.from_config([{"type": "tsumugi_overlay"}])

        assert len(pipeline.effects) == 1
        effect = pipeline.effects[0]
        assert isinstance(effect, TsumugiOverlayEffect)

        main_stream = MagicMock()
        context = VideoEffectContext(duration_seconds=8.0, fps=30, resolution=(1920, 1080))

        effect.apply(main_stream, context)

        mock_input.assert_called_once_with(TSUMUGI_OVERLAY_PATH)
        main_stream.overlay.assert_called_once()
        args = main_stream.overlay.call_args.kwargs
        assert args["x"] == 1920 - 459 - 20
        assert args["y"] == 1080 - 918


class TestTsumugiOverlayAssets:
    def test_default_asset_and_sample_run_exist(self):
        repo_root = Path(__file__).resolve().parents[2]
        overlay_path = (repo_root / TSUMUGI_OVERLAY_PATH).resolve()
        subtitles_path = (repo_root / "runs" / "20251013_083832" / "subtitles.srt").resolve()
        expected_overlay_path = (
            repo_root / "assets" / "春日部つむぎ立ち絵公式_v2.0" / "春日部つむぎ立ち絵公式_v1.1.1.png"
        ).resolve()
        expected_subtitles_path = (repo_root / "runs" / "20251013_083832" / "subtitles.srt").resolve()

        assert overlay_path == expected_overlay_path
        assert subtitles_path == expected_subtitles_path
        assert overlay_path.is_file()
        assert subtitles_path.is_file()
