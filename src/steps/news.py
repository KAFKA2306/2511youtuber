"""
Simplified NewsCollector with Bucket Rotation.
Minimal complexity while preventing topic repetition.
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

from src.core.step import Step
from src.models import NewsItem
from src.providers.base import Provider, execute_with_fallback
from src.tracking import AimTracker
from src.utils.history import gather_recent_topics
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Simple keyword lists for entity detection
ENTITY_KEYWORDS = [
    "日経平均", "TOPIX", "S&P500", "NYダウ", "NASDAQ",
    "ドル円", "ビットコイン", "イーサリアム",
    "日銀", "FRB", "原油", "金相場", "半導体",
    "アサヒ", "トヨタ", "ソニー", "エヌビディア", "テスラ",
]


class NewsCollector(Step):
    """
    Simplified NewsCollector.
    1. Round-robin bucket selection (skips saturated buckets)
    2. Fetch candidates
    3. Filter by entity overlap with history
    """
    name = "collect_news"
    output_filename = "news.json"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        providers: List[Provider],
        query_buckets: Dict[str, str] | None = None,
        bucket_schedule: str | None = None,
        fetch_count: int = 10,
        final_count: int = 3,
        cooldown_hours: int = 24,
        recent_topics_runs: int = 30,
        **kwargs,  # Absorb legacy params
    ):
        super().__init__(run_id, run_dir)
        self.providers = providers
        self.query_buckets = query_buckets or {}
        self.bucket_schedule = bucket_schedule
        self.fetch_count = fetch_count
        self.final_count = final_count
        self.recent_topics_runs = recent_topics_runs

    def execute(self, inputs: Dict[str, Path]) -> Path:
        tracker = AimTracker.get_instance(self.run_id)
        start = time.time()

        # 1. Select bucket (skip saturated ones)
        bucket_key, query = self._select_bucket()
        logger.info(f"Selected: {bucket_key} -> {query}")

        # 2. Fetch
        items = execute_with_fallback(
            self.providers, query=query, count=self.fetch_count, recent_topics_note=""
        )
        logger.info(f"Fetched {len(items)} items")

        # 3. Filter duplicates
        recent = gather_recent_topics(self.run_dir, self.run_id, self.recent_topics_runs)
        filtered = self._filter_duplicates(items, recent)
        logger.info(f"After filter: {len(filtered)}/{len(items)} items")

        if not filtered:
            raise ValueError("All news filtered out by cooldown")

        final = filtered[:self.final_count]

        # Track & save
        tracker.track_prompt(
            step_name="collect_news", template_name="bucket",
            prompt=query, inputs={"bucket": bucket_key},
            output=json.dumps([i.title for i in final], ensure_ascii=False),
            model="rule", duration=time.time() - start,
        )
        return self._save(final)

    def _select_bucket(self) -> Tuple[str, str]:
        """Select first non-saturated bucket (round-robin by run timestamp)."""
        if self.bucket_schedule and self.bucket_schedule in self.query_buckets:
            return self.bucket_schedule, self.query_buckets[self.bucket_schedule]

        recent = gather_recent_topics(self.run_dir, self.run_id, self.recent_topics_runs)
        saturated = self._get_saturated_entities(recent)
        logger.info(f"Saturated: {saturated}")

        # Try buckets in order, pick first non-saturated
        bucket_keys = list(self.query_buckets.keys())
        # Rotate starting point based on run_id hash
        start_idx = hash(self.run_id) % len(bucket_keys) if bucket_keys else 0
        
        for i in range(len(bucket_keys)):
            key = bucket_keys[(start_idx + i) % len(bucket_keys)]
            query = self.query_buckets[key]
            # Check if any query keyword is saturated
            query_entities = self._extract_entities(query)
            if not (query_entities & saturated):
                logger.info(f"Bucket '{key}' OK")
                return key, query
            logger.info(f"Bucket '{key}' saturated, skip")

        # Fallback: use first bucket anyway
        key = bucket_keys[start_idx % len(bucket_keys)]
        return key, self.query_buckets[key]

    def _filter_duplicates(self, items: List[NewsItem], recent: List[str]) -> List[NewsItem]:
        """Remove items whose entities overlap with recent topics."""
        saturated = self._get_saturated_entities(recent)
        result = []
        seen_urls = set()
        
        for item in items:
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            
            item_entities = self._extract_entities(item.title)
            if not (item_entities & saturated):
                result.append(item)
        return result

    def _get_saturated_entities(self, topics: List[str]) -> set:
        """Extract all entities from recent topics."""
        entities = set()
        for topic in topics:
            entities.update(self._extract_entities(topic))
        return entities

    def _extract_entities(self, text: str) -> set:
        """Simple keyword matching."""
        return {kw for kw in ENTITY_KEYWORDS if kw in text}

    def _save(self, items: List[NewsItem]) -> Path:
        path = self.get_output_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([i.model_dump(mode="json") for i in items], f, ensure_ascii=False, indent=2)
        return path
