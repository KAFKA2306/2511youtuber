from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImageFontStub:
    size: int
    path: str | None = None


def truetype(font: str | None = None, size: int = 12, **_: object) -> ImageFontStub:
    if font:
        path = Path(font)
        if not path.exists():
            raise OSError(f"Font file not found: {font}")
        return ImageFontStub(size=size, path=str(path))
    return ImageFontStub(size=size, path=None)


def load_default() -> ImageFontStub:
    return ImageFontStub(size=12, path=None)


__all__ = ["ImageFontStub", "truetype", "load_default"]
