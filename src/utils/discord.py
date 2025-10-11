import json
import os
from pathlib import Path
from typing import Iterable

import requests


def resolve_webhook(env_keys: Iterable[str] | None = None) -> str | None:
    keys = tuple(env_keys or ("DISCORD_WEBHOOK_URL",))
    for key in keys:
        value = os.getenv(key)
        if value:
            return value.strip()
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / "config" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() in keys:
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
        if title and summary:
            lines.append(f"- {title}：{summary}")
        elif title:
            lines.append(f"- {title}")
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

    news_lines = _news_lines(Path(outputs.get("collect_news", "")), max_news)
    youtube_url = _youtube_url(Path(outputs.get("upload_youtube", "")))
    if not youtube_url and outputs.get("render_video"):
        youtube_url = str(outputs["render_video"])

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
