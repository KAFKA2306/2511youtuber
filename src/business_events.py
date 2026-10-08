"""Business event observations are read-only; unverified outcomes are never revenue."""

from __future__ import annotations

UNVERIFIED = "UNVERIFIED"


def summarize_requests(issues: list[dict]) -> dict:
    """Count distinct public issue requests, never infer sales or CTA clicks."""
    seen: set[int] = set()
    count = 0
    for issue in issues:
        number = issue.get("number")
        if not isinstance(number, int) or number in seen:
            continue
        if issue.get("pull_request") or issue.get("state") != "open":
            continue
        seen.add(number)
        count += 1
    return {"open_requests": count, "revenue": UNVERIFIED, "cta_clicks": UNVERIFIED}
