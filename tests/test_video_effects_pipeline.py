from __future__ import annotations

from src.providers.video_effects import (
    TSUMUGI_OVERLAY_OFFSET,
    KenBurnsEffect,
    TsumugiOverlayEffect,
    VideoEffectContext,
    VideoEffectPipeline,
    _overlay_position,
)


def test_video_effect_pipeline_from_config_creates_instances() -> None:
    config_items = [
        {"type": "ken_burns", "pan_mode": "right_to_left", "max_zoom": 1.3},
        {"type": "overlay", "enabled": False, "image_path": "ignored.png"},
        {"type": "tsumugi_overlay", "offset": {"right": 10}},
    ]

    pipeline = VideoEffectPipeline.from_config(config_items)

    assert [effect.__class__.__name__ for effect in pipeline.effects] == [
        "KenBurnsEffect",
        "TsumugiOverlayEffect",
    ]


def test_overlay_position_calculates_expected_coordinates() -> None:
    position = _overlay_position((1920, 1080), (400, 300), anchor="top_left", offset={"left": 10, "top": 20})

    assert position == (10, 20)

    bottom_right = _overlay_position((1920, 1080), (400, 300), anchor="bottom_right", offset={"right": 30, "bottom": 40})
    assert bottom_right == (1920 - 400 - 30, 1080 - 300 - 40)


def test_ken_burns_pan_mode_changes_expression() -> None:
    context = VideoEffectContext(duration_seconds=10, fps=30, resolution=(1920, 1080))
    effect = KenBurnsEffect(pan_mode="left_to_right")

    x_expr, y_expr = effect._pan_expressions(context)

    assert x_expr.startswith('(iw - iw/zoom) *')
    assert 'min(on/' in x_expr
    assert y_expr == 'ih/2 - (ih/zoom/2)'


def test_tsumugi_overlay_default_offset_applies() -> None:
    effect = TsumugiOverlayEffect()

    assert effect.overlay.offset == TSUMUGI_OVERLAY_OFFSET
