import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Dict, List

import litellm

from src.core.step import Step
from src.providers.base import Provider, execute_with_fallback
from src.providers.news import GeminiNewsProvider, PerplexityNewsProvider
from src.tracking import AimTracker
from src.utils.config import NewsProvidersConfig, load_prompts
from src.utils.history import gather_recent_topics
from src.utils.secrets import load_secret_values


class NewsCollector(Step):
    name = "collect_news"
    output_filename = "news.json"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        query: str = "金融ニュース",
        count: int = 3,
        recent_topics_runs: int = 0,
        recent_topics_max_chars: int = 0,
        recent_topics_min_token_length: int = 2,
        recent_topics_stopwords: List[str] | None = None,
        providers_config: NewsProvidersConfig | None = None,
    ):
        super().__init__(run_id, run_dir)
        self.query = query
        self.count = count
        self.recent_topics_runs = recent_topics_runs
        self.recent_topics_max_chars = recent_topics_max_chars
        self.recent_topics_min_token_length = max(1, recent_topics_min_token_length)
        stopwords = recent_topics_stopwords or []
        self.recent_topics_stopwords = {self._normalize_word(word) for word in stopwords if word}
        self.providers_config = providers_config

    def select_topic(self, recent_topics_note: str) -> str:
        prompts = load_prompts()
        topic_prompts = prompts.get("topic_selection")
        if not topic_prompts:
            return self.query
        api_keys = load_secret_values("GEMINI_API_KEY")
        if not api_keys:
            return self.query
        user_prompt = topic_prompts["user_template"].format(recent_topics_note=recent_topics_note)
        response = litellm.completion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[
                {"role": "system", "content": topic_prompts["system"]},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=512,
            api_key=api_keys[0],
        )
        content = response.choices[0].message.content.strip()
        cleaned = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(cleaned)
        return result["query"]

    def execute(self, inputs: Dict[str, Path]) -> Path:
        recent_topics = gather_recent_topics(self.run_dir, self.run_id, self.recent_topics_runs)
        base_recent_text = " / ".join(recent_topics)
        recent_tokens = self._tokenize(base_recent_text)
        tracker = AimTracker.get_instance(self.run_id)
        recent_note = self._build_recent_note(base_recent_text, recent_tokens)
        selected_query = self.select_topic(recent_note)
        prompt_data = {"query": selected_query, "count": self.count, "recent_topics_note": recent_note}
        prompt = json.dumps(prompt_data, ensure_ascii=False)
        start = time.time()
        candidates = execute_with_fallback(
            self._build_providers(),
            query=selected_query,
            count=self.count,
            recent_topics_note=recent_note,
        )
        duration = time.time() - start
        filtered = []
        for item in candidates:
            tokens = self._tokenize(f"{item.title} {item.summary}")
            if tokens & recent_tokens:
                continue
            filtered.append(item)
        news_items = filtered[: self.count]
        if not news_items:
            raise ValueError("新規テーマが見つかりませんでした")
        tracker.track_prompt(
            step_name="collect_news",
            template_name="news_collection",
            prompt=prompt,
            inputs={
                "query": self.query,
                "count": self.count,
                "recent_topics_note": recent_note,
            },
            output=json.dumps([{"title": item.title} for item in news_items], ensure_ascii=False),
            model="perplexity/gemini",
            duration=duration,
        )

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([item.model_dump(mode="json") for item in news_items], f, ensure_ascii=False, indent=2)
        return output_path

    def _build_recent_note(self, base_text: str, tokens: set[str]) -> str:
        note = base_text.strip()
        if tokens:
            banned = ", ".join(sorted(tokens))
            note = f"{note} / 禁止キーワード: {banned}" if note else f"禁止キーワード: {banned}"
        if self.recent_topics_max_chars > 0:
            note = note[: self.recent_topics_max_chars]
        return note or "直近テーマ情報なし"

    def _normalize_word(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKC", str(value)).lower().strip()
        replacements = {
            "日経平均株価": "日経",
            "日経平均": "日経",
            "日経225": "日経",
            "s&p500": "sp500",
            "s&p": "sp500",
            "ドル/円": "ドル円",
            "米ドル": "ドル",
            "ビットコイン": "btc",
            "イーサリアム": "eth",
        }
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        return normalized

    def _tokenize(self, value: str) -> set[str]:
        if not value:
            return set()
        normalized = self._normalize_word(value)
        particle_pattern = r"(が|の|を|に|は|で|と|も|から|まで|より|など|へ|や)"
        tokens = re.split(r"[^0-9a-zA-Z一-龠ぁ-ゔァ-ヴー]+|" + particle_pattern, normalized)
        result = {token for token in tokens if token and len(token) >= self.recent_topics_min_token_length}
        return {token for token in result if token not in self.recent_topics_stopwords}

    def _build_providers(self) -> List[Provider]:
        providers: List[Provider] = []
        config = self.providers_config
        if config and config.perplexity and config.perplexity.enabled:
            providers.append(
                PerplexityNewsProvider(
                    model=config.perplexity.model,
                    temperature=config.perplexity.temperature,
                    max_tokens=config.perplexity.max_tokens,
                    search_recency_filter=config.perplexity.search_recency_filter,
                )
            )
        else:
            providers.append(PerplexityNewsProvider())
        providers.append(GeminiNewsProvider())
        return providers
