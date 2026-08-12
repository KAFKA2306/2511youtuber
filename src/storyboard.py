from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator


AssetKind = Literal["image", "video", "audio"]
AssetRole = Literal[
    "first_frame",
    "last_frame",
    "reference_image",
    "reference_video",
    "reference_audio",
]
GapPolicy = Literal["allow", "forbid"]


class ReferenceAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    kind: AssetKind
    uri: str = Field(min_length=1)
    role: AssetRole
    byte_size: int | None = Field(default=None, ge=0)
    duration_seconds: float | None = Field(default=None, gt=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    fps: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def role_matches_kind(self) -> "ReferenceAsset":
        expected = {
            "first_frame": "image",
            "last_frame": "image",
            "reference_image": "image",
            "reference_video": "video",
            "reference_audio": "audio",
        }[self.role]
        if self.kind != expected:
            raise ValueError(f"asset role {self.role!r} requires kind {expected!r}")
        return self


class TypographyCue(BaseModel):
    text: str = Field(min_length=1)
    reveal: str = ""
    emphasis: str = ""


class Shot(BaseModel):
    shot_id: str = Field(min_length=1)
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)
    message: str = Field(min_length=1, max_length=240)
    composition: str = ""
    subject_state: str = ""
    motion: list[str] = Field(default_factory=list)
    transition_in: str = ""
    typography: list[TypographyCue] = Field(default_factory=list)
    style_invariants: list[str] = Field(default_factory=list)
    reference_asset_ids: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    source_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_contract(self) -> "Shot":
        if self.end_sec <= self.start_sec:
            raise ValueError("end_sec must be greater than start_sec")
        nonempty_lines = [line.strip() for line in self.message.splitlines() if line.strip()]
        if len(nonempty_lines) != 1:
            raise ValueError("one-shot-one-message lint: message must be one non-empty line")
        if re.search(r"(?:^|\s)[-*]\s+\S+", self.message):
            raise ValueError("one-shot-one-message lint: list-like messages are not allowed")
        return self


class VideoStoryboard(BaseModel):
    storyboard_id: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0)
    aspect_ratio: str = Field(default="16:9", min_length=1)
    resolution_target: str = Field(default="1080P", min_length=1)
    global_style: str = ""
    reference_assets: list[ReferenceAsset] = Field(default_factory=list)
    shots: list[Shot] = Field(min_length=1)
    negative_constraints: list[str] = Field(default_factory=list)
    source_evidence_ids: list[str] = Field(default_factory=list)
    prompt_version: str = Field(default="storyboard-v1", min_length=1)
    gap_policy: GapPolicy = "allow"

    @model_validator(mode="after")
    def validate_timeline_and_references(self) -> "VideoStoryboard":
        asset_ids = [asset.asset_id for asset in self.reference_assets]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("reference asset IDs must be unique")

        shot_ids = [shot.shot_id for shot in self.shots]
        if len(shot_ids) != len(set(shot_ids)):
            raise ValueError("shot IDs must be unique")

        known_assets = set(asset_ids)
        previous_end: float | None = None
        ordered = sorted(
            self.shots,
            key=lambda item: (item.start_sec, item.end_sec, item.shot_id),
        )
        for shot in ordered:
            if shot.end_sec > self.duration_seconds + 1e-9:
                raise ValueError(f"shot {shot.shot_id} exceeds storyboard duration")
            if previous_end is not None:
                if shot.start_sec < previous_end - 1e-9:
                    raise ValueError(f"shot {shot.shot_id} overlaps the previous shot")
                if (
                    self.gap_policy == "forbid"
                    and shot.start_sec > previous_end + 1e-9
                ):
                    raise ValueError(f"gap before shot {shot.shot_id} is forbidden")
            missing = set(shot.reference_asset_ids) - known_assets
            if missing:
                raise ValueError(
                    f"shot {shot.shot_id} references unknown assets: {sorted(missing)}"
                )
            previous_end = shot.end_sec

        if self.gap_policy == "forbid":
            if ordered[0].start_sec > 1e-9:
                raise ValueError("timeline must start at 0 when gap_policy=forbid")
            if ordered[-1].end_sec < self.duration_seconds - 1e-9:
                raise ValueError("timeline must reach storyboard duration when gap_policy=forbid")
        return self
