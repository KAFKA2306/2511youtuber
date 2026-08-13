import json
from pathlib import Path

import pytest

from src.services.performance_feedback import (
    PerformanceObservation,
    build_prompt_context,
    load_observations,
    render_prompt_context,
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
        "evidence_url": f"https://example.invalid/evidence/{video_id}",
    }


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


def test_insufficient_sample_never_generates_success_pattern() -> None:
    rows = [PerformanceObservation.from_mapping(_row(str(i), "AI")) for i in range(4)]
    context = build_prompt_context(rows, min_sample_size=5)
    assert context["state"] == "insufficient_sample"
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
    assert context["state"] == "measured"
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
