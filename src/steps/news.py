import json
import time
from pathlib import Path
from typing import Dict, List

from src.core.step import Step
from src.providers.base import Provider, execute_with_fallback
from src.providers.news import GeminiNewsProvider, PerplexityNewsProvider
from src.tracking import AimTracker
from src.utils.config import NewsProvidersConfig
from src.utils.history import gather_recent_topics


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
        gemini_model: str = "gemini/gemini-1.5-flash-latest",
    ):
        super().__init__(run_id, run_dir)
        self.query = query
        self.count = count
        self.recent_topics_runs = recent_topics_runs
        self.recent_topics_max_chars = recent_topics_max_chars
        self.providers_config = providers_config
        self.gemini_model = gemini_model

    def execute(self, inputs: Dict[str, Path]) -> Path:
        recent_topics = gather_recent_topics(self.run_dir, self.run_id, self.recent_topics_runs)
        recent_note = " / ".join(recent_topics) if recent_topics else "直近テーマ情報なし"
        if self.recent_topics_max_chars > 0:
            recent_note = recent_note[: self.recent_topics_max_chars]

        tracker = AimTracker.get_instance(self.run_id)
        prompt_data = {"query": self.query, "count": self.count, "recent_topics_note": recent_note}
        prompt = json.dumps(prompt_data, ensure_ascii=False)

        start = time.time()
        news_items = execute_with_fallback(
            self._build_providers(),
            query=self.query,
            count=self.count,
            recent_topics_note=recent_note,
        )
        duration = time.time() - start

        if not news_items:
            raise ValueError("ニュースが見つかりませんでした")

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
        providers.append(GeminiNewsProvider(model=self.gemini_model))
        return providers
