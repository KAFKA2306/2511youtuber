import json
from pathlib import Path
from typing import Dict, List

from src.providers.base import execute_with_fallback
from src.providers.news import PerplexityNewsProvider
from src.core.step import Step
from src.utils.config import NewsProvidersConfig


class NewsCollector(Step):
    name = "collect_news"
    output_filename = "news.json"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        query: str = "金融ニュース",
        count: int = 3,
        providers_config: NewsProvidersConfig | None = None,
    ):
        super().__init__(run_id, run_dir)
        self.query = query
        self.count = count
        self.providers_config = providers_config

    def execute(self, inputs: Dict[str, Path]) -> Path:
        news_items = execute_with_fallback(self._build_providers(), query=self.query, count=self.count)
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([item.model_dump(mode="json") for item in news_items], f, ensure_ascii=False, indent=2)
        return output_path

    def _build_providers(self) -> List[PerplexityNewsProvider]:
        providers: List[PerplexityNewsProvider] = []
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
        return providers or [PerplexityNewsProvider()]
