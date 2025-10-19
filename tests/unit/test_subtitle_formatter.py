import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.steps.subtitle import SubtitleFormatter
from src.utils.config import Config


CONFIG = Config.load()
SUBTITLE_CFG = CONFIG.steps.subtitle
VIDEO_CFG = CONFIG.steps.video
STYLE_CFG = VIDEO_CFG.subtitles


def _margins() -> tuple[int, int]:
    return int(STYLE_CFG.margin_l or 0), int(STYLE_CFG.margin_r or 0)


def test_estimate_max_chars_per_line_respects_margins() -> None:
    margin_l, margin_r = _margins()
    value = SubtitleFormatter.estimate_max_chars_per_line(
        VIDEO_CFG.resolution,
        SUBTITLE_CFG.width_per_char_pixels,
        SUBTITLE_CFG.min_visual_width,
        SUBTITLE_CFG.max_visual_width,
        margin_l=margin_l,
        margin_r=margin_r,
    )
    safe_width = SubtitleFormatter.safe_pixel_width(VIDEO_CFG.resolution, margin_l, margin_r)
    expected = max(
        SUBTITLE_CFG.min_visual_width,
        min(
            SUBTITLE_CFG.max_visual_width,
            int(max(safe_width, 0) / SUBTITLE_CFG.width_per_char_pixels),
        ),
    )
    assert value == expected


def test_wrap_visual_line_enforces_limit(tmp_path) -> None:
    margin_l, margin_r = _margins()
    max_chars = SubtitleFormatter.estimate_max_chars_per_line(
        VIDEO_CFG.resolution,
        SUBTITLE_CFG.width_per_char_pixels,
        SUBTITLE_CFG.min_visual_width,
        SUBTITLE_CFG.max_visual_width,
        margin_l=margin_l,
        margin_r=margin_r,
    )
    wrap_width = SubtitleFormatter.safe_pixel_width(VIDEO_CFG.resolution, margin_l, margin_r)
    formatter = SubtitleFormatter(
        "run",
        tmp_path,
        max_chars_per_line=max_chars,
        width_per_char_pixels=SUBTITLE_CFG.width_per_char_pixels,
        wrap_width_pixels=wrap_width,
        font_path=STYLE_CFG.font_path,
        font_size=STYLE_CFG.font_size,
    )
    lines = formatter._wrap_visual_line("かながながい文章で句点がありませんしかし読みやすくしたい", max_chars)
    widths = [formatter._text_width(line) for line in lines if line]
    assert widths
    assert all(width <= wrap_width for width in widths)
