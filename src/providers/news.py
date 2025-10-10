from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List

import requests
import yaml

from src.models import NewsItem
from src.providers.base import Provider
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

    def is_available(self) -> bool:
        return bool(self.api_keys)

    def execute(self, query: str = "", count: int = 3, **kwargs) -> List[NewsItem]:
        if not self.api_keys:
            raise ValueError("Perplexity API key not configured")

        prompt = self._build_prompt(query=query, count=count)

        for attempt in range(len(self.api_keys)):
            api_key = self.api_keys[self.current_key_index]
            try:
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
                                "content": "You are an assistant that produces structured financial news summaries in pure Japanese.",
                            },
                            {
                                "role": "user",
                                "content": prompt,
                            },
                        ],
                    },
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return self._parse_response(content, count)
            except Exception as exc:  # pragma: no cover - network call
                logger.warning(
                    "Perplexity request failed",
                    error=str(exc),
                    attempt=attempt,
                    key_index=self.current_key_index,
                )
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

        raise RuntimeError("All Perplexity API attempts failed")

    def _build_prompt(self, query: str, count: int) -> str:
        topic = query or "最新の日本の金融・経済ニュース"
        return (
            f"{topic}を題材に、信頼できる情報源から取得した最新ニュースを{count}件まとめてください。"
            "応答は必ず以下のJSON配列形式で出力してください。"
            "各要素は title, summary, url, published_at(ISO8601) のキーを持ちます。"
            "不要な説明やコードブロック記法は含めないでください。"
        )

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

class DummyNewsProvider(Provider):
    name = "dummy_news"
    priority = 999

    def is_available(self) -> bool:
        return True

    def execute(self, query: str = "", count: int = 3, **kwargs) -> List[NewsItem]:
        logger.info("Using dummy news provider", count=count)

        return [
            NewsItem(
                title="日本経済が予想を上回る成長を記録",
                summary="最新の経済指標によると、日本経済は前四半期比で三パーセントの成長を記録しました。専門家らは、この成長が今後も続くと予想しています。",
                url="https://example.com/news/1",
                published_at=datetime.now(timezone.utc),
            ),
            NewsItem(
                title="円相場が大きく変動、投資家が注目",
                summary="外国為替市場では円が大きく変動しています。アナリストたちは、今後の金融政策がこの動きに影響を与えると見ています。",
                url="https://example.com/news/2",
                published_at=datetime.now(timezone.utc),
            ),
            NewsItem(
                title="新興企業の株価が急上昇",
                summary="テクノロジー分野の新興企業の株価が今週、過去最高値を記録しました。投資家たちは、同社の革新的な技術に大きな期待を寄せています。",
                url="https://example.com/news/3",
                published_at=datetime.now(timezone.utc),
            ),
        ][:count]
