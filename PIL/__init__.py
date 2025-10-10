"""Lightweight stub of the Pillow (PIL) package used for testing.

Only the functionality required by our codebase is implemented.  The design
intentionally mirrors Pillow's public modules (`Image`, `ImageDraw`, and
`ImageFont`) so existing import statements continue to work.
"""

from importlib import import_module

Image = import_module(".Image", __name__)
ImageDraw = import_module(".ImageDraw", __name__)
ImageFont = import_module(".ImageFont", __name__)

__all__ = ["Image", "ImageDraw", "ImageFont"]
