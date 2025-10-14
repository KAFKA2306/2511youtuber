from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List

import requests

from src.models import NewsItem
from src.utils.config import load_prompts
from src.utils.secrets import load_secret_values


class PerplexityNewsProvider:
    name = "perplexity"
    api_url = "https://api.perplexity.ai/chat/completions"

    def __init__(
        self,
        model: str = "sonar",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        search_recency_filter: str | None = None,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.search_recency_filter = search_recency_filter
        self.api_keys = load_secret_values("PERPLEXITY_API_KEY")
        self.prompts = load_prompts()["news_collection"]

    def is_available(self) -> bool:
        return bool(self.api_keys)

    def execute(self, query: str = "", count: int = 3, **kwargs) -> List[NewsItem]:
        topic = query or "最新の日本の金融・経済ニュース"
        prompt = self.prompts["user_template"].format(topic=topic, count=count)
        api_key = self.api_keys[0]

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": self.prompts["system"]},
                {"role": "user", "content": prompt},
            ],
        }
        if self.search_recency_filter:
            payload["search_recency_filter"] = self.search_recency_filter

        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(self._strip_code_fences(content))
        items = [self._normalise_item(entry) for entry in parsed]
        return items[:count]

    def _strip_code_fences(self, raw: str) -> str:
        cleaned = raw.strip()
        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("\n", 1)[0]
        return cleaned.strip()

    def _normalise_item(self, entry: dict) -> NewsItem:
        title = str(entry.get("title", "")).strip()
        summary = str(entry.get("summary", "")).strip()
        url = str(entry.get("url", "")).strip()
        published_at = self._parse_datetime(str(entry.get("published_at", "")).strip())
        return NewsItem(title=title, summary=summary, url=url, published_at=published_at)

    def _parse_datetime(self, value: str) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
