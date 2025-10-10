from __future__ import annotations

from typing import Any, Iterable

from .Image import ImageStub


class Draw:
    """Collects drawing commands for :class:`ImageStub`."""

    def __init__(self, image: ImageStub) -> None:
        self.image = image

    def rectangle(self, xy: Iterable[tuple[int, int]], fill: Any | None = None, outline: Any | None = None) -> None:
        self.image.record("rectangle", points=[tuple(point) for point in xy], fill=fill, outline=outline)

    def text(self, xy: tuple[int, int], text: str, font: Any | None = None, fill: Any | None = None) -> None:
        self.image.record(
            "text",
            position=tuple(xy),
            text=str(text),
            font_size=getattr(font, "size", None),
            fill=fill,
        )


__all__ = ["Draw"]
