import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.steps.subtitle import SubtitleFormatter


def test_estimate_max_chars_per_line_respects_margins() -> None:
    value = SubtitleFormatter.estimate_max_chars_per_line(
        "1920x1080",
        70,
        16,
        40,
        margin_l=360,
        margin_r=480,
    )
    assert value == 16


def test_wrap_visual_line_enforces_limit(tmp_path) -> None:
    font_path = Path(__file__).resolve().parents[2] / "assets/fonts/ZenMaruGothic-Bold.ttf"
    max_chars = SubtitleFormatter.estimate_max_chars_per_line(
        "1920x1080",
        70,
        16,
        40,
        margin_l=360,
        margin_r=480,
    )
    formatter = SubtitleFormatter(
        "run",
        tmp_path,
        max_chars_per_line=max_chars,
        width_per_char_pixels=70,
        wrap_width_pixels=SubtitleFormatter.safe_pixel_width("1920x1080", 360, 480),
        font_path=str(font_path),
        font_size=24,
    )
    lines = formatter._wrap_visual_line("かながながい文章で句点がありませんしかし読みやすくしたい", max_chars)
    widths = [formatter._text_width(line) for line in lines if line]
    assert widths
    assert all(width <= formatter.wrap_width_pixels for width in widths)
