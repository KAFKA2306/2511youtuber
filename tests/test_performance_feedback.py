import json
from pathlib import Path

import pytest

from src.services.performance_feedback import (
    SOURCE_PROVIDER,
    PerformanceObservation,
    build_prompt_context,
    collect_measurement_ledger,
    load_observations,
    load_prompt_context,
    normalize_report_response,
    render_prompt_context,
    write_measurement_ledger,
)


def _row(video_id: str, topic: str, duration: float = 120.0) -> dict:
    return {
        "video_id": video_id,
        "topic": topic,
        "period_start": "2026-08-01",
        "period_end": "2026-08-07",
        "retrieved_at": "2026-08-08T00:00:00Z",
        "views": 100,
        "likes": 10,
        "averageViewDuration": duration,
        "estimatedMinutesWatched": 200,
        "evidence_url": "https://youtubeanalytics.googleapis.com/v2/reports",
        "source_provider": SOURCE_PROVIDER,
        "source_query": {
            "ids": "channel==MINE",
            "startDate": "2026-08-01",
            "endDate": "2026-08-07",
            "metrics": "views,likes,averageViewDuration,estimatedMinutesWatched",
            "dimensions": "video",
            "filters": f"video=={video_id}",
        },
    }


def _response(video_id: str, *, duration: float = 120.0) -> dict:
    return {
        "columnHeaders": [
            {"name": "video"},
            {"name": "views"},
            {"name": "likes"},
            {"name": "averageViewDuration"},
            {"name": "estimatedMinutesWatched"},
        ],
        "rows": [[video_id, 100, 10, duration, 200]],
    }


class _Request:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return self.response


class _Reports:
    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            return _Request(error=self.error)
        return _Request(response=self.responses.pop(0))


class _Service:
    def __init__(self, responses=None, error=None):
        self._reports = _Reports(responses=responses, error=error)

    def reports(self):
        return self._reports


def test_not_instrumented_is_not_measured_zero(tmp_path: Path) -> None:
    path = tmp_path / "performance.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "youtube-performance.v1",
                "measurement_state": "not_instrumented",
                "observations": [],
            }
        ),
        encoding="utf-8",
    )
    assert load_observations(path) == []


def test_missing_api_metric_fails_closed() -> None:
    row = _row("a", "AI")
    del row["averageViewDuration"]
    with pytest.raises(ValueError, match="averageViewDuration"):
        PerformanceObservation.from_mapping(row)


def test_insufficient_evidence_never_generates_success_pattern() -> None:
    rows = [
        PerformanceObservation.from_mapping(_row(str(i), "AI"))
        for i in range(4)
    ]
    context = build_prompt_context(rows, min_sample_size=5)
    assert context["state"] == "INSUFFICIENT_EVIDENCE"
    assert context["patterns"] == []
    assert render_prompt_context(context) == ""


def test_pattern_requires_repeated_support_and_keeps_evidence() -> None:
    raw = [
        _row("a", "AI", 200),
        _row("b", "AI", 190),
        _row("c", "rates", 180),
        _row("d", "markets", 100),
        _row("e", "earnings", 90),
    ]
    rows = [PerformanceObservation.from_mapping(row) for row in raw]
    context = build_prompt_context(rows, min_sample_size=5)
    assert context["state"] == "MEASURED"
    assert context["patterns"] == [{"topic": "AI", "supporting_videos": 2}]
    assert {item["video_id"] for item in context["evidence"]} >= {"a", "b"}
    rendered = render_prompt_context(context)
    assert "AI" in rendered
    assert "Evidence video IDs" in rendered


def test_duplicate_video_id_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "performance.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "youtube-performance.v1",
                "measurement_state": "measured",
                "observations": [_row("a", "AI"), _row("a", "AI")],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate video_id"):
        load_observations(path)


def test_api_response_is_normalized_by_column_name() -> None:
    response = {
        "columnHeaders": [
            {"name": "likes"},
            {"name": "video"},
            {"name": "estimatedMinutesWatched"},
            {"name": "views"},
            {"name": "averageViewDuration"},
        ],
        "rows": [[10, "vid-1", 200, 100, 123.5]],
    }
    observation = normalize_report_response(
        response,
        video_id="vid-1",
        topic="AI",
        period_start="2026-08-01",
        period_end="2026-08-07",
        retrieved_at="2026-08-08T00:00:00Z",
        source_query={"filters": "video==vid-1"},
    )
    assert observation is not None
    assert observation.views == 100
    assert observation.likes == 10
    assert observation.average_view_duration == 123.5


def test_collection_writes_traceable_measured_ledger(tmp_path: Path) -> None:
    service = _Service(responses=[_response("a"), _response("b")])
    ledger = collect_measurement_ledger(
        service,
        videos=[
            {"video_id": "a", "topic": "AI"},
            {"video_id": "b", "topic": "AI"},
        ],
        period_start="2026-08-01",
        period_end="2026-08-07",
        retrieved_at="2026-08-08T00:00:00Z",
    )
    path = write_measurement_ledger(tmp_path / "performance.json", ledger)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["measurement_state"] == "measured"
    assert payload["source_provider"] == SOURCE_PROVIDER
    assert [row["video_id"] for row in payload["observations"]] == ["a", "b"]
    assert service._reports.calls[0]["ids"] == "channel==MINE"
    assert service._reports.calls[0]["dimensions"] == "video"
    assert service._reports.calls[0]["filters"] == "video==a"


def test_external_api_failure_is_not_silently_replaced() -> None:
    service = _Service(error=RuntimeError("analytics unavailable"))
    with pytest.raises(RuntimeError, match="analytics unavailable"):
        collect_measurement_ledger(
            service,
            videos=[{"video_id": "a", "topic": "AI"}],
            period_start="2026-08-01",
            period_end="2026-08-07",
        )


def test_prompt_context_loads_evidence_trace_from_ledger(tmp_path: Path) -> None:
    rows = [
        _row("a", "AI", 200),
        _row("b", "AI", 190),
        _row("c", "rates", 180),
        _row("d", "markets", 100),
        _row("e", "earnings", 90),
    ]
    path = tmp_path / "performance.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "youtube-performance.v1",
                "measurement_state": "measured",
                "observations": rows,
            }
        ),
        encoding="utf-8",
    )
    context = load_prompt_context(path)
    assert context["state"] == "MEASURED"
    assert context["source_path"] == str(path)
    assert {item["video_id"] for item in context["evidence"]} >= {"a", "b"}
