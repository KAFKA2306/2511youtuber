from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "youtube-performance.v1"
SOURCE_PROVIDER = "youtubeAnalytics.reports.query"
SOURCE_ENDPOINT = "https://youtubeanalytics.googleapis.com/v2/reports"
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
    source_provider: str
    source_query: dict[str, str]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PerformanceObservation":
        missing = [
            key
            for key in (
                "video_id",
                "topic",
                "period_start",
                "period_end",
                "retrieved_at",
                "evidence_url",
                "source_provider",
                "source_query",
                *REQUIRED_METRICS,
            )
            if key not in value
        ]
        if missing:
            raise ValueError(
                f"performance observation missing fields: {', '.join(missing)}"
            )

        video_id = str(value["video_id"]).strip()
        topic = str(value["topic"]).strip()
        if not video_id or not topic:
            raise ValueError("video_id and topic must not be empty")
        if not str(value["evidence_url"]).startswith("https://"):
            raise ValueError("performance evidence_url must be HTTPS")
        if str(value["source_provider"]) != SOURCE_PROVIDER:
            raise ValueError("unsupported performance source_provider")
        source_query = value["source_query"]
        if not isinstance(source_query, dict):
            raise ValueError("source_query must be a mapping")

        for key in ("period_start", "period_end", "retrieved_at"):
            _parse_iso_date(value[key], key)
        if str(value["period_start"]) > str(value["period_end"]):
            raise ValueError(
                "performance observation period_start must not exceed period_end"
            )

        views = _non_negative_integer(value["views"], "views")
        likes = _non_negative_integer(value["likes"], "likes")
        average_view_duration = _non_negative(
            value["averageViewDuration"], "averageViewDuration"
        )
        estimated_minutes_watched = _non_negative(
            value["estimatedMinutesWatched"], "estimatedMinutesWatched"
        )

        return cls(
            video_id=video_id,
            topic=topic,
            period_start=str(value["period_start"]),
            period_end=str(value["period_end"]),
            retrieved_at=str(value["retrieved_at"]),
            views=views,
            likes=likes,
            average_view_duration=average_view_duration,
            estimated_minutes_watched=estimated_minutes_watched,
            evidence_url=str(value["evidence_url"]),
            source_provider=SOURCE_PROVIDER,
            source_query={str(k): str(v) for k, v in source_query.items()},
        )

    def to_mapping(self) -> dict[str, Any]:
        data = asdict(self)
        data["averageViewDuration"] = data.pop("average_view_duration")
        data["estimatedMinutesWatched"] = data.pop("estimated_minutes_watched")
        return data


def build_youtube_analytics_service(credentials: Any) -> Any:
    from googleapiclient.discovery import build

    return build("youtubeAnalytics", "v2", credentials=credentials)


def fetch_video_observation(
    service: Any,
    *,
    video_id: str,
    topic: str,
    period_start: str,
    period_end: str,
    retrieved_at: str | None = None,
) -> PerformanceObservation | None:
    query = {
        "ids": "channel==MINE",
        "startDate": period_start,
        "endDate": period_end,
        "metrics": ",".join(REQUIRED_METRICS),
        "dimensions": "video",
        "filters": f"video=={video_id}",
    }
    response = service.reports().query(**query).execute()
    return normalize_report_response(
        response,
        video_id=video_id,
        topic=topic,
        period_start=period_start,
        period_end=period_end,
        retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat(),
        source_query=query,
    )


def collect_measurement_ledger(
    service: Any,
    *,
    videos: Sequence[Mapping[str, str]],
    period_start: str,
    period_end: str,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    fetched_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    observations: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in videos:
        video_id = str(item.get("video_id", "")).strip()
        topic = str(item.get("topic", "")).strip()
        if not video_id or not topic:
            raise ValueError("each analytics target requires video_id and topic")
        if video_id in seen:
            raise ValueError(f"duplicate analytics target video_id: {video_id}")
        seen.add(video_id)
        observation = fetch_video_observation(
            service,
            video_id=video_id,
            topic=topic,
            period_start=period_start,
            period_end=period_end,
            retrieved_at=fetched_at,
        )
        if observation is not None:
            observations.append(observation.to_mapping())

    return {
        "schema_version": SCHEMA_VERSION,
        "measurement_state": "measured",
        "source_provider": SOURCE_PROVIDER,
        "retrieved_at": fetched_at,
        "observations": observations,
    }


def write_measurement_ledger(path: Path, ledger: Mapping[str, Any]) -> Path:
    observations = ledger.get("observations")
    if not isinstance(observations, list):
        raise ValueError("performance ledger observations must be a list")
    if ledger.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported performance schema_version")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(ledger), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def normalize_report_response(
    response: Mapping[str, Any],
    *,
    video_id: str,
    topic: str,
    period_start: str,
    period_end: str,
    retrieved_at: str,
    source_query: Mapping[str, str],
) -> PerformanceObservation | None:
    headers = response.get("columnHeaders")
    if not isinstance(headers, list):
        raise ValueError("YouTube Analytics response missing columnHeaders")
    names = [
        str(header.get("name", ""))
        for header in headers
        if isinstance(header, Mapping)
    ]
    required_columns = ["video", *REQUIRED_METRICS]
    missing = [name for name in required_columns if name not in names]
    if missing:
        raise ValueError(
            "YouTube Analytics response missing columns: " + ", ".join(missing)
        )

    rows = response.get("rows")
    if rows is None:
        return None
    if not isinstance(rows, list):
        raise ValueError("YouTube Analytics response rows must be a list")
    if len(rows) > 1:
        raise ValueError("single-video analytics query returned multiple rows")
    if not rows:
        return None
    row = rows[0]
    if not isinstance(row, list) or len(row) != len(names):
        raise ValueError("YouTube Analytics response row does not match headers")

    mapped = dict(zip(names, row))
    if str(mapped["video"]) != video_id:
        raise ValueError("YouTube Analytics response video does not match request")

    return PerformanceObservation.from_mapping(
        {
            "video_id": video_id,
            "topic": topic,
            "period_start": period_start,
            "period_end": period_end,
            "retrieved_at": retrieved_at,
            "views": mapped["views"],
            "likes": mapped["likes"],
            "averageViewDuration": mapped["averageViewDuration"],
            "estimatedMinutesWatched": mapped["estimatedMinutesWatched"],
            "evidence_url": SOURCE_ENDPOINT,
            "source_provider": SOURCE_PROVIDER,
            "source_query": dict(source_query),
        }
    )


def load_observations(path: Path) -> list[PerformanceObservation]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported performance schema_version")
    state = payload.get("measurement_state")
    if state == "not_instrumented":
        return []
    if state != "measured":
        raise ValueError(f"unsupported measurement_state: {state!r}")
    rows = payload.get("observations")
    if not isinstance(rows, list):
        raise ValueError("performance observations must be a list")
    observations = [PerformanceObservation.from_mapping(row) for row in rows]
    ids = [row.video_id for row in observations]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate video_id in performance observations")
    return observations


def build_prompt_context(
    observations: Iterable[PerformanceObservation],
    *,
    min_sample_size: int = MIN_SAMPLE_SIZE,
) -> dict[str, Any]:
    rows = list(observations)
    if min_sample_size < 2:
        raise ValueError("min_sample_size must be at least 2")
    if len(rows) < min_sample_size:
        return {
            "state": "INSUFFICIENT_EVIDENCE",
            "sample_size": len(rows),
            "minimum_sample_size": min_sample_size,
            "patterns": [],
            "evidence": [],
        }

    median_duration = median(row.average_view_duration for row in rows)
    selected = [
        row for row in rows if row.average_view_duration >= median_duration
    ]
    topic_counts: dict[str, int] = {}
    for row in selected:
        topic_counts[row.topic] = topic_counts.get(row.topic, 0) + 1

    patterns = [
        {"topic": topic, "supporting_videos": count}
        for topic, count in sorted(
            topic_counts.items(), key=lambda item: (-item[1], item[0])
        )
        if count >= 2
    ]
    evidence = [
        {
            "video_id": row.video_id,
            "period_start": row.period_start,
            "period_end": row.period_end,
            "retrieved_at": row.retrieved_at,
            "evidence_url": row.evidence_url,
            "source_provider": row.source_provider,
        }
        for row in selected
    ]
    return {
        "state": "MEASURED" if patterns else "NO_SUPPORTED_PATTERN",
        "sample_size": len(rows),
        "minimum_sample_size": min_sample_size,
        "metric_definition": "averageViewDuration >= sample median",
        "patterns": patterns,
        "evidence": evidence if patterns else [],
    }


def load_prompt_context(
    path: Path,
    *,
    min_sample_size: int = MIN_SAMPLE_SIZE,
) -> dict[str, Any]:
    context = build_prompt_context(
        load_observations(Path(path)),
        min_sample_size=min_sample_size,
    )
    context["source_path"] = str(path)
    return context


def render_prompt_context(context: Mapping[str, Any]) -> str:
    if context.get("state") != "MEASURED":
        return ""
    patterns = context.get("patterns", [])
    evidence = context.get("evidence", [])
    if not patterns or not evidence:
        return ""
    pattern_lines = [
        f"- {item['topic']} (supporting videos: {item['supporting_videos']})"
        for item in patterns
    ]
    evidence_ids = ", ".join(
        sorted({str(item["video_id"]) for item in evidence})
    )
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


def _non_negative_integer(value: Any, field: str) -> int:
    number = _non_negative(value, field)
    if not number.is_integer():
        raise ValueError(f"{field} must be an integer")
    return int(number)
