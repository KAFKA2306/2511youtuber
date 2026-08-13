from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

REQUIRED_METRICS = (
    "views",
    "likes",
    "averageViewDuration",
    "estimatedMinutesWatched",
)
MIN_SAMPLE_SIZE = 5


@dataclass(frozen=True)
class PerformanceObservation:
    video_id: str
    topic: str
    period_start: str
    period_end: str
    retrieved_at: str
    views: int
    likes: int
    average_view_duration: float
    estimated_minutes_watched: float
    evidence_url: str

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "PerformanceObservation":
        missing = [
            key
            for key in (
                "video_id",
                "topic",
                "period_start",
                "period_end",
                "retrieved_at",
                "evidence_url",
                *REQUIRED_METRICS,
            )
            if key not in value
        ]
        if missing:
            raise ValueError(f"performance observation missing fields: {', '.join(missing)}")
        if not str(value["evidence_url"]).startswith("https://"):
            raise ValueError("performance evidence_url must be HTTPS")
        for key in ("period_start", "period_end", "retrieved_at"):
            _parse_iso_date(value[key], key)
        if str(value["period_start"]) > str(value["period_end"]):
            raise ValueError("performance observation period_start must not exceed period_end")
        metrics = {key: _non_negative(value[key], key) for key in REQUIRED_METRICS}
        return cls(
            video_id=str(value["video_id"]).strip(),
            topic=str(value["topic"]).strip(),
            period_start=str(value["period_start"]),
            period_end=str(value["period_end"]),
            retrieved_at=str(value["retrieved_at"]),
            views=int(metrics["views"]),
            likes=int(metrics["likes"]),
            average_view_duration=float(metrics["averageViewDuration"]),
            estimated_minutes_watched=float(metrics["estimatedMinutesWatched"]),
            evidence_url=str(value["evidence_url"]),
        )


def load_observations(path: Path) -> list[PerformanceObservation]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "youtube-performance.v1":
        raise ValueError("unsupported performance schema_version")
    if payload.get("measurement_state") != "measured":
        return []
    rows = payload.get("observations")
    if not isinstance(rows, list):
        raise ValueError("performance observations must be a list")
    observations = [PerformanceObservation.from_mapping(row) for row in rows]
    ids = [row.video_id for row in observations]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate video_id in performance observations")
    return observations


def build_prompt_context(
    observations: Iterable[PerformanceObservation], *, min_sample_size: int = MIN_SAMPLE_SIZE
) -> dict[str, Any]:
    rows = list(observations)
    if min_sample_size < 2:
        raise ValueError("min_sample_size must be at least 2")
    if len(rows) < min_sample_size:
        return {
            "state": "insufficient_sample",
            "sample_size": len(rows),
            "minimum_sample_size": min_sample_size,
            "patterns": [],
            "evidence": [],
        }

    durations = sorted(row.average_view_duration for row in rows)
    median_duration = durations[len(durations) // 2]
    selected = [row for row in rows if row.average_view_duration >= median_duration]
    topic_counts: dict[str, int] = {}
    for row in selected:
        topic_counts[row.topic] = topic_counts.get(row.topic, 0) + 1
    patterns = [
        {"topic": topic, "supporting_videos": count}
        for topic, count in sorted(topic_counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= 2
    ]
    evidence = [
        {
            "video_id": row.video_id,
            "period_start": row.period_start,
            "period_end": row.period_end,
            "retrieved_at": row.retrieved_at,
            "evidence_url": row.evidence_url,
        }
        for row in selected
    ]
    return {
        "state": "measured" if patterns else "no_supported_pattern",
        "sample_size": len(rows),
        "minimum_sample_size": min_sample_size,
        "patterns": patterns,
        "evidence": evidence if patterns else [],
    }


def render_prompt_context(context: dict[str, Any]) -> str:
    if context.get("state") != "measured":
        return ""
    patterns = context.get("patterns", [])
    evidence = context.get("evidence", [])
    if not patterns or not evidence:
        return ""
    pattern_lines = [
        f"- {item['topic']} (supporting videos: {item['supporting_videos']})" for item in patterns
    ]
    evidence_ids = ", ".join(sorted({str(item["video_id"]) for item in evidence}))
    return (
        "\n\n[Measured YouTube performance feedback]\n"
        "Use only as auxiliary context; do not treat correlation as causation.\n"
        + "\n".join(pattern_lines)
        + f"\nEvidence video IDs: {evidence_ids}"
    )


def _parse_iso_date(value: Any, field: str) -> None:
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc


def _non_negative(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if number < 0:
        raise ValueError(f"{field} must be non-negative")
    return number
