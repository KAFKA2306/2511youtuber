from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Tuple


@dataclass
class ImageStub:
    """A minimal in-memory representation of an image."""

    mode: str
    size: Tuple[int, int]
    background: str | Tuple[int, int, int]
    operations: list[dict[str, Any]] = field(default_factory=list)

    def record(self, operation: str, **kwargs: Any) -> None:
        self.operations.append({"operation": operation, **kwargs})

    # Pillow's Image class acts as a context manager.
    def __enter__(self) -> "ImageStub":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def save(self, fp: str | Path, format: str | None = None, **_: Any) -> None:  # noqa: A003
        """Persist the image to disk in a lightweight JSON representation."""

        payload = {
            "mode": self.mode,
            "size": list(self.size),
            "background": self.background,
            "operations": self.operations,
        }
        Path(fp).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def copy(self) -> "ImageStub":
        return ImageStub(self.mode, self.size, self.background, list(self.operations))

    def close(self) -> None:
        # Provided for API compatibility with Pillow's Image.close().
        return None


def new(mode: str, size: Iterable[int], color: str | Tuple[int, int, int] = "black") -> ImageStub:
    width, height = tuple(size)
    return ImageStub(mode=mode, size=(int(width), int(height)), background=color)


def open(fp: str | Path, mode: str | None = None) -> ImageStub:  # noqa: A003
    """Load an image saved by :meth:`ImageStub.save`."""

    path = Path(fp)
    data = json.loads(path.read_text(encoding="utf-8"))
    image = ImageStub(mode=data.get("mode", "RGB"), size=tuple(data.get("size", (0, 0))), background=data.get("background", "black"))
    image.operations = list(data.get("operations", []))
    return image


__all__ = ["ImageStub", "new", "open"]
