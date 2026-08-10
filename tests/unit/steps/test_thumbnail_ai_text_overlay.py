from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops

from src.steps.thumbnail_ai import AIThumbnailGenerator


def _background_bytes(size: tuple[int, int]) -> bytes:
    image = Image.new("RGB", size, "#446688")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_ai_thumbnail_composes_exact_japanese_title_locally(tmp_path: Path) -> None:
    generator = AIThumbnailGenerator(
        "run",
        tmp_path,
        {
            "enabled": True,
            "width": 640,
            "height": 360,
            "text_overlay_enabled": True,
        },
    )

    result = generator._compose_title(_background_bytes((640, 360)), "日銀利上げ")

    with Image.open(BytesIO(result)) as rendered:
        assert rendered.format == "PNG"
        assert rendered.size == (640, 360)
        baseline = Image.new("RGB", rendered.size, "#446688")
        assert ImageChops.difference(rendered.convert("RGB"), baseline).getbbox() is not None


def test_ai_thumbnail_text_overlay_is_enabled_by_default(tmp_path: Path) -> None:
    generator = AIThumbnailGenerator("run", tmp_path, {"enabled": True})
    assert generator.text_overlay_enabled is True
