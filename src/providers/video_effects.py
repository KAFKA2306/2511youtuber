from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Tuple, Type

from ffmpeg.nodes import FilterableStream

from src.utils.config import Config


@dataclass(frozen=True)
class VideoEffectContext:
    duration_seconds: float
    fps: int
    resolution: Tuple[int, int]


class VideoEffect:
    name: str = ""

    def apply(self, stream: FilterableStream, context: VideoEffectContext) -> FilterableStream:
        raise NotImplementedError


EFFECT_REGISTRY: Dict[str, Type[VideoEffect]] = {}


@lru_cache(maxsize=1)
def _subtitle_margins() -> Tuple[int, int]:
    cfg = Config.load()
    video_cfg = cfg.steps.video
    style = video_cfg.subtitles
    if style is None:
        return 0, 0
    left = int(style.margin_l or 0)
    right = int(style.margin_r or 0)
    return left, right


def _offset_value(offset: Dict[str, int] | None, key: str) -> int:
    if not offset:
        return 0
    raw = offset.get(key)
    if raw is None:
        return 0
    return int(raw)


def register_effect(effect_cls: Type[VideoEffect]) -> Type[VideoEffect]:
    EFFECT_REGISTRY[effect_cls.name] = effect_cls
    return effect_cls


class VideoEffectPipeline:
    def __init__(self, effects: Iterable[VideoEffect] | None = None) -> None:
        self.effects: List[VideoEffect] = list(effects or [])

    def apply(self, stream: FilterableStream, context: VideoEffectContext) -> FilterableStream:
        for effect in self.effects:
            stream = effect.apply(stream, context)
        return stream

    @classmethod
    def from_config(cls, config: Iterable[Dict] | None) -> "VideoEffectPipeline":
        effects = []
        for raw in config or []:
            data = raw.model_dump() if hasattr(raw, "model_dump") else raw
            if not data.get("enabled", True):
                continue
            params = {k: v for k, v in data.items() if k not in {"type", "enabled"}}
            effects.append(EFFECT_REGISTRY[data["type"]](**params))
        return cls(effects)


@register_effect
class KenBurnsEffect(VideoEffect):
    name = "ken_burns"

    def __init__(
        self,
        zoom_speed: float = 0.0015,
        max_zoom: float = 1.2,
        hold_frame_factor: float = 1.0,
        pan_mode: str = "center",
    ):
        self.zoom_speed = float(zoom_speed)
        self.max_zoom = float(max_zoom)
        self.hold_frame_factor = max(float(hold_frame_factor), 0.01)
        self.pan_mode = pan_mode

    def apply(self, stream: FilterableStream, context: VideoEffectContext) -> FilterableStream:
        frames = max(int(round(self.hold_frame_factor)), 1)
        x_expr, y_expr = self._pan_expressions(context)
        return stream.filter(
            "zoompan",
            z=f"min(zoom+{self.zoom_speed},{self.max_zoom})",
            d=frames,
            s=f"{context.resolution[0]}x{context.resolution[1]}",
            x=x_expr,
            y=y_expr,
        )

    def _pan_expressions(self, context: VideoEffectContext) -> Tuple[str, str]:
        center_x = "iw/2 - (iw/zoom/2)"
        center_y = "ih/2 - (ih/zoom/2)"
        total_frames = max(int(context.duration_seconds * context.fps), 1)
        progress = f"min(on/{max(total_frames - 1, 1)},1)"
        pan_modes = {
            "left_to_right": (f"(iw - iw/zoom) * {progress}", center_y),
            "right_to_left": (f"(iw - iw/zoom) * (1 - {progress})", center_y),
            "top_to_bottom": (center_x, f"(ih - ih/zoom) * {progress}"),
            "bottom_to_top": (center_x, f"(ih - ih/zoom) * (1 - {progress})"),
        }
        return pan_modes.get(self.pan_mode, (center_x, center_y))


def _overlay_position(
    video_res: Tuple[int, int],
    overlay_res: Tuple[int, int],
    anchor: str = "bottom_right",
    offset: Dict[str, int] | None = None,
) -> Tuple[int, int]:
    offset = offset or {}
    top, right, bottom, left = (int(offset.get(k) or 0) for k in ("top", "right", "bottom", "left"))
    vw, vh = video_res
    ow, oh = overlay_res
    if "left" in anchor:
        x = left
    elif "right" in anchor:
        x = vw - ow - right
    else:
        x = (vw - ow) // 2 + left - right
    if "top" in anchor:
        y = top
    elif "bottom" in anchor:
        y = vh - oh - bottom
    else:
        y = (vh - oh) // 2 + top - bottom
    left_margin, right_margin = _subtitle_margins()
    safe_left = left_margin
    safe_right = vw - right_margin
    if "left" in anchor:
        x = min(max(0, x), max(0, safe_left - ow))
    elif "right" in anchor:
        x = max(min(vw - ow, x), min(vw - ow, safe_right))
    else:
        left_space = max(0, safe_left - ow)
        right_space = max(0, vw - safe_right - ow)
        if right_space >= left_space:
            x = max(min(vw - ow, x), min(vw - ow, safe_right))
        else:
            x = min(max(0, x), max(0, safe_left - ow))
    x = max(0, min(x, vw - ow))
    y = max(0, min(y, vh - oh))
    return x, y


@register_effect
class OverlayEffect(VideoEffect):
    name = "overlay"

    def __init__(
        self,
        image_path: str,
        anchor: str = "bottom_right",
        height_ratio: float | None = None,
        width_ratio: float | None = None,
        height: int | None = None,
        width: int | None = None,
        offset: Dict[str, int] | None = None,
    ):
        self.image_path = image_path
        self.anchor = anchor
        self.height_ratio = height_ratio
        self.width_ratio = width_ratio
        self.height = height
        self.width = width
        self.offset = offset

    def apply(self, stream: FilterableStream, context: VideoEffectContext) -> FilterableStream:
        import ffmpeg

        overlay_stream = ffmpeg.input(self.image_path)
        probe = ffmpeg.probe(self.image_path)
        orig_w = int(probe["streams"][0]["width"])
        orig_h = int(probe["streams"][0]["height"])
        video_w, video_h = context.resolution
        overlay_w, overlay_h = self._dimensions(orig_w, orig_h, video_w, video_h, self.offset)

        if (overlay_w, overlay_h) != (orig_w, orig_h):
            overlay_stream = overlay_stream.filter("scale", overlay_w, overlay_h)

        x, y = _overlay_position(context.resolution, (overlay_w, overlay_h), self.anchor, self.offset)
        return stream.overlay(overlay_stream, x=x, y=y)

    def _dimensions(
        self,
        orig_w: int,
        orig_h: int,
        video_w: int,
        video_h: int,
        offset: Dict[str, int] | None = None,
    ) -> Tuple[int, int]:
        w, h = orig_w, orig_h
        if self.height:
            h = max(int(self.height), 1)
            w = max(int(round(orig_w * (h / orig_h))), 1)
        elif self.width:
            w = max(int(self.width), 1)
            h = max(int(round(orig_h * (w / orig_w))), 1)
        elif self.height_ratio:
            h = max(int(round(video_h * float(self.height_ratio))), 1)
            w = max(int(round(orig_w * (h / orig_h))), 1)
        elif self.width_ratio:
            w = max(int(round(video_w * float(self.width_ratio))), 1)
            h = max(int(round(orig_h * (w / orig_w))), 1)
        left_margin, right_margin = _subtitle_margins()
        left_offset = max(_offset_value(offset, "left"), 0)
        right_offset = max(_offset_value(offset, "right"), 0)
        if "left" in self.anchor:
            bound = max(left_margin - left_offset, 0)
        elif "right" in self.anchor:
            bound = max(right_margin - right_offset, 0)
        else:
            bound = max(max(left_margin - left_offset, 0), max(right_margin - right_offset, 0))
        if bound and bound > 0 and w > bound:
            scale = bound / w
            w = max(int(round(w * scale)), 1)
            h = max(int(round(h * scale)), 1)
        if w > video_w:
            scale = video_w / w
            w = max(int(round(w * scale)), 1)
            h = max(int(round(h * scale)), 1)
        if h > video_h:
            scale = video_h / h
            h = max(int(round(h * scale)), 1)
            w = max(int(round(w * scale)), 1)
        return w, h


@register_effect
class MultiOverlayEffect(VideoEffect):
    name = "multi_overlay"

    def __init__(self, overlays: List[Dict]):
        items: List[OverlayEffect] = []
        for overlay in overlays:
            data = overlay.model_dump() if hasattr(overlay, "model_dump") else dict(overlay)
            if not data.get("enabled", True):
                continue
            params = {k: v for k, v in data.items() if k not in {"type", "enabled"}}
            items.append(OverlayEffect(**params))
        self.overlays = items

    def apply(self, stream: FilterableStream, context: VideoEffectContext) -> FilterableStream:
        for overlay in self.overlays:
            stream = overlay.apply(stream, context)
        return stream


__all__ = [
    "KenBurnsEffect",
    "OverlayEffect",
    "MultiOverlayEffect",
    "VideoEffect",
    "VideoEffectContext",
    "VideoEffectPipeline",
]
