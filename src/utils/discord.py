import json
import os
from pathlib import Path
from typing import Iterable

import requests

from src.utils.secrets import load_secret_values


def resolve_webhook(env_keys: Iterable[str] | None = None) -> str | None:
    keys = tuple(env_keys or ("DISCORD_WEBHOOK_URL",))
    for key in keys:
        value = os.getenv(key)
        if not value:
            secrets = load_secret_values(key, max_keys=1)
            value = secrets[0] if secrets else None
        if value:
            return value.strip()
    return None


def _news_lines(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return []
    items = json.loads(path.read_text(encoding="utf-8"))
    lines: list[str] = []
    for item in items[:limit]:
        title = str(item.get("title", "")).strip()
        summary = str(item.get("summary", "")).strip()
        parts = [part for part in (title, summary) if part]
        if parts:
            lines.append(f"- {'：'.join(parts)}")
    return lines


def _youtube_url(path: Path) -> str | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("video_url"):
        return str(data["video_url"]).strip()
    if data.get("video_id"):
        return f"https://www.youtube.com/watch?v={data['video_id']}"
    return None


def post_run_summary(
    run_id: str,
    outputs: dict[str, str],
    *,
    webhook_keys: Iterable[str] | None = None,
    max_news: int = 3,
) -> None:
    webhook = resolve_webhook(webhook_keys)
    if not webhook:
        return

    news_path = outputs.get("collect_news")
    news_lines = _news_lines(Path(news_path), max_news) if news_path else []
    upload_path = outputs.get("upload_youtube")
    youtube_url = _youtube_url(Path(upload_path)) if upload_path else None
    if not youtube_url:
        render_path = outputs.get("render_video")
        youtube_url = str(render_path) if render_path else None

    lines: list[str] = []
    if youtube_url:
        lines.append(f"📹 {youtube_url}")
    if news_lines:
        lines.append("📰 今日のニュースまとめ:")
        lines.extend(news_lines)
    if not lines:
        return

    content = f"Run {run_id}\n" + "\n".join(lines)
    requests.post(webhook, json={"content": content}, timeout=5)
