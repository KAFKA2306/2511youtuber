from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List

import requests
import yaml

from src.models import NewsItem
from src.providers.base import Provider
from src.utils.config import load_prompts
from src.utils.logger import get_logger
from src.utils.secrets import load_secret_values

logger = get_logger(__name__)


class PerplexityNewsProvider(Provider):
    name = "perplexity_news"
    priority = 1
    api_url = "https://api.perplexity.ai/chat/completions"

    def __init__(self, model: str = "sonar", temperature: float = 0.2, max_tokens: int = 2048):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_keys = load_secret_values("PERPLEXITY_API_KEY")
        self.current_key_index = 0
        self.prompts = load_prompts()["news_collection"]

    def is_available(self) -> bool:
        return bool(self.api_keys)

    def execute(self, query: str = "", count: int = 3, **kwargs) -> List[NewsItem]:
        topic = query or "最新の日本の金融・経済ニュース"
        prompt = self.prompts["user_template"].format(topic=topic, count=count)
        api_key = self.api_keys[self.current_key_index]

        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "messages": [
                    {
                        "role": "system",
                        "content": self.prompts["system"],
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return self._parse_response(content, count)

    def _parse_response(self, raw: str, count: int) -> List[NewsItem]:
        raw = raw.strip()

        if raw.startswith("```") and raw.endswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("\n", 1)[0]

        parsed = None
        for parser in (self._parse_json, self._parse_yaml):
            parsed = parser(raw)
            if parsed is not None:
                break

        if parsed is None:
            raise ValueError("Failed to parse Perplexity response")

        items: List[NewsItem] = []
        for entry in parsed:
            item = self._normalise_item(entry)
            items.append(item)
            if len(items) >= count:
                break

        if not items:
            raise ValueError("Perplexity response did not contain any news items")

        return items

    def _parse_json(self, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, list) else None

    def _parse_yaml(self, raw: str):
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError:
            return None
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            return data["items"]
        return data if isinstance(data, list) else None

    def _normalise_item(self, entry: dict) -> NewsItem:
        title = str(entry.get("title", "")).strip()
        summary = str(entry.get("summary", "")).strip()
        url = str(entry.get("url", "")).strip()
        published_at_raw = str(entry.get("published_at", "")).strip()
        published_at = self._parse_datetime(published_at_raw)

        if not title or not summary:
            raise ValueError("Incomplete news item")

        return NewsItem(
            title=title,
            summary=summary,
            url=url,
            published_at=published_at,
        )

    def _parse_datetime(self, value: str) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)
