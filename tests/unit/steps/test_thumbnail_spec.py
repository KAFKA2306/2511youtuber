from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
from PIL import Image

from src.steps.thumbnail import ThumbnailGenerator


def _thumbnail_config() -> dict:
    raw = yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))
    cfg = dict(raw["steps"]["thumbnail"])
    cfg["enabled"] = True
    cfg["randomize_palette"] = False
    return cfg


def test_default_thumbnail_contract_matches_issue_28() -> None:
    cfg = _thumbnail_config()
    assert cfg["background_color"] == "#fef155"
    assert cfg["title_color"] == "#EB001B"
    assert cfg["outline_inner_color"] == "#FFFFFF"
    assert cfg["outline_inner_width"] in (2, 3)
    assert cfg["outline_outer_color"] == "#000000"
    assert 4 <= cfg["outline_outer_width"] <= 6
    assert cfg["outline_outer_width"] > cfg["outline_inner_width"]
    assert 8 <= cfg["safe_margin_pct"] <= 10
    assert cfg["preview_width"] == 200
    assert cfg["title_height_min_pct"] == 30
    assert cfg["title_height_max_pct"] == 40


def test_render_order_is_black_then_white_then_red(tmp_path: Path) -> None:
    generator = ThumbnailGenerator("run", tmp_path, _thumbnail_config())

    class Font:
        def getlength(self, text: str) -> int:
            return len(text) * 20

    class Draw:
        def __init__(self) -> None:
            self.calls = []

        def text(self, xy, text, **kwargs) -> None:
            self.calls.append(kwargs)

        def textbbox(self, xy, text, font=None):
            return (xy[0], xy[1], xy[0] + 100, xy[1] + 40)

    draw = Draw()
    generator._render_text(draw, "速報", Font(), generator.title_color, 60, 1160, left_edge=115)
    assert [call["fill"] for call in draw.calls] == ["#000000", "#FFFFFF", "#EB001B"]
    assert draw.calls[0]["stroke_width"] == 6
    assert draw.calls[1]["stroke_width"] == 3
    assert "stroke_width" not in draw.calls[2]


def test_render_emits_mobile_preview_and_audit_metadata(tmp_path: Path) -> None:
    generator = ThumbnailGenerator("run", tmp_path, _thumbnail_config())
    script = SimpleNamespace(segments=[SimpleNamespace(text="日銀利上げ", speaker="春日部つむぎ")])

    with patch("src.steps.thumbnail.load_script", return_value=script):
        output = generator.execute({"generate_script": Path("unused.json")})

    assert output.exists()
    with Image.open(output) as image:
        assert image.size == (1280, 720)
        assert image.getpixel((0, 0)) == (254, 241, 85)

    preview = output.with_name("thumbnail.preview.png")
    assert preview.exists()
    with Image.open(preview) as image:
        assert image.size == (200, 112)

    metadata_path = output.with_name("thumbnail.metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["copy"] == "日銀利上げ"
    assert metadata["outline_white_px"] == 3
    assert metadata["outline_black_px"] == 6
    assert metadata["safe_margin_pct"] == 9
    assert metadata["preview_width_px"] == 200
    assert metadata["background_color"] == "#fef155"
    assert metadata["text_color"] == "#EB001B"
    assert metadata["title_height_pct"] <= 40
