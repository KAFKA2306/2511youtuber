from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import requests

from src.storyboard import ReferenceAsset, VideoStoryboard


class VideoGenerationProvider(Protocol):
    name: str
    model: str

    def compile_request(self, storyboard: VideoStoryboard) -> dict[str, Any]: ...

    def create_task(self, storyboard: VideoStoryboard) -> "VideoGenerationAudit": ...

    def query_task(self, task_id: str) -> dict[str, Any]: ...


class StoryboardPromptCompiler:
    version = "storyboard-compiler-v1"

    def compile(self, storyboard: VideoStoryboard) -> str:
        lines = [
            f"Storyboard {storyboard.storyboard_id}",
            f"Global style: {storyboard.global_style or 'unspecified'}",
        ]
        if storyboard.negative_constraints:
            lines.append("Global negative constraints: " + "; ".join(storyboard.negative_constraints))

        assets = {asset.asset_id: asset for asset in storyboard.reference_assets}
        for shot in sorted(storyboard.shots, key=lambda item: (item.start_sec, item.end_sec, item.shot_id)):
            fields = [
                f"[{shot.start_sec:.3f}-{shot.end_sec:.3f}s] {shot.shot_id}",
                f"message={shot.message}",
            ]
            if shot.composition:
                fields.append(f"composition={shot.composition}")
            if shot.subject_state:
                fields.append(f"subject_state={shot.subject_state}")
            if shot.motion:
                fields.append("motion=" + "; ".join(shot.motion))
            if shot.transition_in:
                fields.append(f"transition_in={shot.transition_in}")
            if shot.typography:
                typography = [
                    "/".join(filter(None, (cue.text, cue.reveal, cue.emphasis)))
                    for cue in shot.typography
                ]
                fields.append("typography=" + "; ".join(typography))
            if shot.style_invariants:
                fields.append("style_invariants=" + "; ".join(shot.style_invariants))
            if shot.reference_asset_ids:
                refs = [assets[asset_id] for asset_id in shot.reference_asset_ids]
                fields.append("references=" + ", ".join(f"{ref.asset_id}:{ref.role}" for ref in refs))
            if shot.negative_constraints:
                fields.append("negative_constraints=" + "; ".join(shot.negative_constraints))
            lines.append(" | ".join(fields))
        return "\n".join(lines)


@dataclass(frozen=True)
class VideoGenerationAudit:
    storyboard_id: str
    provider: str
    model: str
    request_parameters: dict[str, Any]
    compiled_prompt: str
    task_id: str
    response: dict[str, Any]
    generated_asset_hash: str | None
    generation_timestamp: str
    compiler_version: str
    h3_context_ir: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "storyboard_id": self.storyboard_id,
            "provider": self.provider,
            "model": self.model,
            "request_parameters": self.request_parameters,
            "compiled_prompt": self.compiled_prompt,
            "task_id": self.task_id,
            "response": self.response,
            "generated_asset_hash": self.generated_asset_hash,
            "generation_timestamp": self.generation_timestamp,
            "compiler_version": self.compiler_version,
            "h3_context_ir": self.h3_context_ir,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class MiniMaxH3Provider:
    name = "minimax"
    model = "MiniMax-H3"
    create_url = "https://api.minimax.io/v2/video_generation"
    query_url = "https://api.minimax.io/v2/query/video_generation/{task_id}"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        session: requests.Session | None = None,
        compiler: StoryboardPromptCompiler | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.session = session or requests.Session()
        self.compiler = compiler or StoryboardPromptCompiler()
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        return bool(self.api_key)

    def validate(self, storyboard: VideoStoryboard) -> None:
        if storyboard.duration_seconds != int(storyboard.duration_seconds):
            raise ValueError("MiniMax-H3 duration must be an integer number of seconds")
        duration = int(storyboard.duration_seconds)
        if not 4 <= duration <= 15:
            raise ValueError("MiniMax-H3 duration must be between 4 and 15 seconds")
        if storyboard.resolution_target not in {"768P", "2K"}:
            raise ValueError("MiniMax-H3 resolution must be 768P or 2K")
        if storyboard.aspect_ratio not in {"21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "adaptive"}:
            raise ValueError("unsupported MiniMax-H3 aspect ratio")

        assets = storyboard.reference_assets
        first = [asset for asset in assets if asset.role == "first_frame"]
        last = [asset for asset in assets if asset.role == "last_frame"]
        refs = [asset for asset in assets if asset.role.startswith("reference_")]
        if len(first) > 1 or len(last) > 1:
            raise ValueError("MiniMax-H3 accepts at most one first frame and one last frame")
        if (first or last) and refs:
            raise ValueError("MiniMax-H3 first/last-frame mode cannot be mixed with reference mode")
        if sum(asset.role == "reference_image" for asset in assets) > 9:
            raise ValueError("MiniMax-H3 accepts at most 9 reference images")
        if sum(asset.role == "reference_video" for asset in assets) > 3:
            raise ValueError("MiniMax-H3 accepts at most 3 reference videos")
        if sum(asset.role == "reference_audio" for asset in assets) > 3:
            raise ValueError("MiniMax-H3 accepts at most 3 reference audio files")

        for asset in assets:
            self._validate_asset_metadata(asset)

    @staticmethod
    def _validate_asset_metadata(asset: ReferenceAsset) -> None:
        if asset.kind == "image" and asset.byte_size is not None and asset.byte_size > 30 * 1024 * 1024:
            raise ValueError(f"{asset.asset_id}: MiniMax-H3 image exceeds 30 MB")
        if asset.kind == "video" and asset.byte_size is not None and asset.byte_size > 50 * 1024 * 1024:
            raise ValueError(f"{asset.asset_id}: MiniMax-H3 video exceeds 50 MB")
        if asset.kind == "audio" and asset.byte_size is not None and asset.byte_size > 15 * 1024 * 1024:
            raise ValueError(f"{asset.asset_id}: MiniMax-H3 audio exceeds 15 MB")
        if asset.kind in {"video", "audio"} and asset.duration_seconds is not None:
            if not 2 <= asset.duration_seconds <= 15:
                raise ValueError(f"{asset.asset_id}: reference media duration must be 2-15 seconds")
        if asset.width is not None and not 256 <= asset.width <= 5760:
            raise ValueError(f"{asset.asset_id}: width must be 256-5760 px")
        if asset.height is not None and not 256 <= asset.height <= 5760:
            raise ValueError(f"{asset.asset_id}: height must be 256-5760 px")
        if asset.width and asset.height:
            ratio = asset.width / asset.height
            if not 0.4 <= ratio <= 2.5:
                raise ValueError(f"{asset.asset_id}: aspect ratio must be within [0.4, 2.5]")
        if asset.kind == "video" and asset.fps is not None and not 23.976 <= asset.fps <= 60:
            raise ValueError(f"{asset.asset_id}: fps must be within [23.976, 60]")

    def compile_request(self, storyboard: VideoStoryboard) -> dict[str, Any]:
        self.validate(storyboard)
        prompt = self.compiler.compile(storyboard)
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for asset in storyboard.reference_assets:
            content.append(self._asset_content(asset))

        image_to_video = any(asset.role in {"first_frame", "last_frame"} for asset in storyboard.reference_assets)
        return {
            "model": self.model,
            "content": content,
            "resolution": storyboard.resolution_target,
            "duration": int(storyboard.duration_seconds),
            "ratio": "adaptive" if image_to_video else storyboard.aspect_ratio,
        }

    @staticmethod
    def _asset_content(asset: ReferenceAsset) -> dict[str, Any]:
        content_type = {
            "image": "image_url",
            "video": "video_url",
            "audio": "audio_url",
        }[asset.kind]
        return {"type": content_type, content_type: asset.uri, "role": asset.role}

    def create_task(self, storyboard: VideoStoryboard) -> VideoGenerationAudit:
        if not self.api_key:
            raise RuntimeError("MINIMAX_API_KEY is required for a live MiniMax request")
        request_body = self.compile_request(storyboard)
        response = self.session.post(
            self.create_url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=request_body,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        task_id = str(payload["task_id"])
        return VideoGenerationAudit(
            storyboard_id=storyboard.storyboard_id,
            provider=self.name,
            model=self.model,
            request_parameters={key: value for key, value in request_body.items() if key != "content"},
            compiled_prompt=request_body["content"][0]["text"],
            task_id=task_id,
            response=payload,
            generated_asset_hash=None,
            generation_timestamp=datetime.now(timezone.utc).isoformat(),
            compiler_version=self.compiler.version,
        )

    def query_task(self, task_id: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("MINIMAX_API_KEY is required for a live MiniMax request")
        response = self.session.get(
            self.query_url.format(task_id=task_id),
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def audit_json(audit: VideoGenerationAudit) -> str:
        return json.dumps(audit.as_dict(), ensure_ascii=False, sort_keys=True, indent=2)
