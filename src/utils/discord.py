from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

import requests

from src.utils.discord_config import load_discord_config, resolve_path

SUMMARY_SETTINGS = load_discord_config()["summary"]
ENV_PATH = resolve_path(SUMMARY_SETTINGS["environment_file"])
VIDEO_PREFIX = SUMMARY_SETTINGS["video_prefix"]
NEWS_HEADING = SUMMARY_SETTINGS["news_heading"]
NEWS_FORMAT = SUMMARY_SETTINGS["news_format"]
NEWS_TITLE_ONLY_FORMAT = SUMMARY_SETTINGS["news_title_only_format"]
YOUTUBE_BASE = SUMMARY_SETTINGS["youtube_base"]
NEWS_OUTPUT_KEY = SUMMARY_SETTINGS["news_output_key"]
VIDEO_OUTPUT_KEY = SUMMARY_SETTINGS["video_output_key"]
RENDER_OUTPUT_KEY = SUMMARY_SETTINGS["render_output_key"]
MAX_NEWS = int(SUMMARY_SETTINGS["max_news"])


def _env_values(keys: Iterable[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        name = key.strip()
        if name in keys and name not in values:
            values[name] = value.strip()
    return values


def resolve_webhook(env_keys: Iterable[str] | None = None) -> str | None:
    keys = tuple(env_keys or SUMMARY_SETTINGS["webhook_keys"])
    for key in keys:
        value = os.getenv(key)
        if value:
            return value.strip()
    values = _env_values(keys)
    for key in keys:
        if key in values:
            return values[key]
    return None


def _news_lines(path: Path, limit: int) -> list[str]:
    items = json.loads(path.read_text(encoding="utf-8"))[:limit]
    lines: list[str] = []
    for item in items:
        title = str(item.get("title", "")).strip()
        summary = str(item.get("summary", "")).strip()
        if not title:
            continue
        if summary:
            lines.append(NEWS_FORMAT.format(title=title, summary=summary))
        else:
            lines.append(NEWS_TITLE_ONLY_FORMAT.format(title=title))
    return lines


def _youtube_url(path: Path) -> str | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("video_url"):
        return str(data["video_url"]).strip()
    if data.get("video_id"):
        return f"{YOUTUBE_BASE}{data['video_id']}"
    return None


def post_run_summary(
    run_id: str,
    outputs: dict[str, str],
    *,
    webhook_keys: Iterable[str] | None = None,
    max_news: int | None = None,
) -> None:
    webhook = resolve_webhook(webhook_keys)
    if not webhook:
        return
    news_path = outputs.get(NEWS_OUTPUT_KEY)
    news_lines = _news_lines(Path(news_path), max_news or MAX_NEWS) if news_path else []
    youtube_path = outputs.get(VIDEO_OUTPUT_KEY)
    youtube_url = _youtube_url(Path(youtube_path)) if youtube_path else None
    render_url = outputs.get(RENDER_OUTPUT_KEY)
    if not youtube_url and render_url:
        youtube_url = str(render_url)
    lines: list[str] = []
    if youtube_url:
        lines.append(f"{VIDEO_PREFIX}{youtube_url}")
    if news_lines:
        lines.append(NEWS_HEADING)
        lines.extend(news_lines)
    if not lines:
        return
    content = f"Run {run_id}\n" + "\n".join(lines)
    requests.post(webhook, json={"content": content}, timeout=5)
