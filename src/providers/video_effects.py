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
    """Base class for declarative ffmpeg video effects."""

    name: str = ""

    def apply(
        self, stream: FilterableStream, context: VideoEffectContext
    ) -> FilterableStream:  # pragma: no cover - interface
        raise NotImplementedError


EFFECT_REGISTRY: Dict[str, Type[VideoEffect]] = {}


def register_effect(effect_cls: Type[VideoEffect]) -> Type[VideoEffect]:
    if not effect_cls.name:
        raise ValueError("VideoEffect subclasses must define a name")
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
        if not config:
            return cls(effects)

        for raw in config:
            if not raw:
                continue

            if hasattr(raw, "model_dump"):
                raw = raw.model_dump()

            effect_type = raw.get("type")
            if not effect_type:
                raise ValueError("Video effect configuration requires a 'type' field")

            if not raw.get("enabled", True):
                continue

            effect_cls = EFFECT_REGISTRY.get(effect_type)
            if not effect_cls:
                raise ValueError(f"Unknown video effect type: {effect_type}")

            params = {k: v for k, v in raw.items() if k not in {"type", "enabled"}}
            effect = effect_cls(**params)
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


__all__ = [
    "KenBurnsEffect",
    "VideoEffect",
    "VideoEffectContext",
    "VideoEffectPipeline",
]
