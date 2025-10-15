from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple, Type

from ffmpeg.nodes import FilterableStream


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
TSUMUGI_OVERLAY_PATH = "assets/春日部つむぎ立ち絵公式_v2.0/春日部つむぎ立ち絵公式_v1.1.1.png"
TSUMUGI_OVERLAY_OFFSET = {"right": 20, "bottom": 0}


def register_effect(effect_cls: Type[VideoEffect]) -> Type[VideoEffect]:
    EFFECT_REGISTRY[effect_cls.name] = effect_cls
    return effect_cls


class VideoEffectPipeline:
    def __init__(self, effects: Sequence[VideoEffect] | None = None) -> None:
        self.effects: List[VideoEffect] = list(effects or [])

    def apply(self, stream: FilterableStream, context: VideoEffectContext) -> FilterableStream:
        current = stream
        for effect in self.effects:
            current = effect.apply(current, context)
        return current

    @classmethod
    def from_config(cls, config: Iterable[Dict] | None) -> "VideoEffectPipeline":
        effects: List[VideoEffect] = []

        for raw in config or []:
            data = raw.model_dump() if hasattr(raw, "model_dump") else raw
            if not data.get("enabled", True):
                continue

            params = {k: v for k, v in data.items() if k not in {"type", "enabled"}}
            effect = EFFECT_REGISTRY[data["type"]](**params)
            effects.append(effect)

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
    ) -> None:
        self.zoom_speed = float(zoom_speed)
        self.max_zoom = float(max_zoom)
        self.hold_frame_factor = max(float(hold_frame_factor), 0.01)
        self.pan_mode = pan_mode

    def apply(self, stream: FilterableStream, context: VideoEffectContext) -> FilterableStream:
        frames = max(int(round(self.hold_frame_factor)), 1)
        x_expr, y_expr = self._resolve_pan_expressions(context)

        return stream.filter(
            "zoompan",
            z=f"min(zoom+{self.zoom_speed},{self.max_zoom})",
            d=frames,
            s=f"{context.resolution[0]}x{context.resolution[1]}",
            x=x_expr,
            y=y_expr,
        )

    def _resolve_pan_expressions(self, context: VideoEffectContext) -> Tuple[str, str]:
        center_x = "iw/2 - (iw/zoom/2)"
        center_y = "ih/2 - (ih/zoom/2)"

        total_frames = max(int(context.duration_seconds * context.fps), 1)
        progress_denominator = max(total_frames - 1, 1)
        progress_expr = f"min(on/{progress_denominator},1)"

        if self.pan_mode == "left_to_right":
            return f"(iw - iw/zoom) * {progress_expr}", center_y
        if self.pan_mode == "right_to_left":
            return f"(iw - iw/zoom) * (1 - {progress_expr})", center_y
        if self.pan_mode == "top_to_bottom":
            return center_x, f"(ih - ih/zoom) * {progress_expr}"
        if self.pan_mode == "bottom_to_top":
            return center_x, f"(ih - ih/zoom) * (1 - {progress_expr})"

        return center_x, center_y


def _resolve_overlay_position(
    video_resolution: Tuple[int, int],
    overlay_resolution: Tuple[int, int],
    anchor: str = "bottom_right",
    offset: Dict[str, int] | None = None,
) -> Tuple[int, int]:
    offset = offset or {}
    top = int(offset.get("top") or 0)
    right = int(offset.get("right") or 0)
    bottom = int(offset.get("bottom") or 0)
    left = int(offset.get("left") or 0)
    video_width, video_height = video_resolution
    overlay_width, overlay_height = overlay_resolution

    if "left" in anchor:
        x = left
    elif "right" in anchor:
        x = video_width - overlay_width - right
    else:
        x = (video_width - overlay_width) // 2 + left - right

    if "top" in anchor:
        y = top
    elif "bottom" in anchor:
        y = video_height - overlay_height - bottom
    else:
        y = (video_height - overlay_height) // 2 + top - bottom

    return max(0, x), max(0, y)


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
    ) -> None:
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
        original_width = int(probe["streams"][0]["width"])
        original_height = int(probe["streams"][0]["height"])
        video_width, video_height = context.resolution

        overlay_width, overlay_height = self._resolve_overlay_dimensions(
            original_width,
            original_height,
            video_width,
            video_height,
        )

        if (overlay_width, overlay_height) != (original_width, original_height):
            overlay_stream = overlay_stream.filter("scale", overlay_width, overlay_height)

        x, y = _resolve_overlay_position(
            context.resolution,
            (overlay_width, overlay_height),
            self.anchor,
            self.offset,
        )

        return stream.overlay(overlay_stream, x=x, y=y)

    def _resolve_overlay_dimensions(
        self,
        original_width: int,
        original_height: int,
        video_width: int,
        video_height: int,
    ) -> Tuple[int, int]:
        width = original_width
        height = original_height

        if self.height:
            height = max(int(self.height), 1)
            width = max(int(round(original_width * (height / original_height))), 1)
        elif self.width:
            width = max(int(self.width), 1)
            height = max(int(round(original_height * (width / original_width))), 1)
        elif self.height_ratio:
            height = max(int(round(video_height * float(self.height_ratio))), 1)
            width = max(int(round(original_width * (height / original_height))), 1)
        elif self.width_ratio:
            width = max(int(round(video_width * float(self.width_ratio))), 1)
            height = max(int(round(original_height * (width / original_width))), 1)

        return width, height


@register_effect
class TsumugiOverlayEffect(VideoEffect):
    name = "tsumugi_overlay"

    def __init__(
        self,
        image_path: str = TSUMUGI_OVERLAY_PATH,
        anchor: str = "bottom_right",
        height_ratio: float | None = 0.85,
        width_ratio: float | None = None,
        height: int | None = None,
        width: int | None = None,
        offset: Dict[str, int] | None = None,
    ) -> None:
        resolved_offset = offset if offset is not None else TSUMUGI_OVERLAY_OFFSET
        self.overlay = OverlayEffect(
            image_path=image_path,
            anchor=anchor,
            height_ratio=height_ratio,
            width_ratio=width_ratio,
            height=height,
            width=width,
            offset=dict(resolved_offset),
        )

    def apply(self, stream: FilterableStream, context: VideoEffectContext) -> FilterableStream:
        return self.overlay.apply(stream, context)


__all__ = [
    "KenBurnsEffect",
    "OverlayEffect",
    "TSUMUGI_OVERLAY_OFFSET",
    "TSUMUGI_OVERLAY_PATH",
    "TsumugiOverlayEffect",
    "VideoEffect",
    "VideoEffectContext",
    "VideoEffectPipeline",
]
