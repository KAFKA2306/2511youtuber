"""News collection with post-fetch diversity selection."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.core.step import Step
from src.models import NewsItem
from src.providers.base import Provider, execute_with_fallback
from src.providers.llm import load_prompt_template
from src.tracking import AimTracker
from src.utils.history import gather_recent_topics
from src.utils.logger import get_logger
from src.utils.text import extract_code_block

logger = get_logger(__name__)

# Regex patterns for entity detection. The first alternative is the normalized key.
ENTITY_PATTERNS = [
    r"日経平均(?:株価)?",
    r"TOPIX",
    r"S&P500|S&P\s*500",
    r"NYダウ|ダウ平均",
    r"NASDAQ|ナスダック",
    r"ドル円|円ドル|USD/JPY",
    r"ユーロ円|EUR/JPY",
    r"ビットコイン|BTC",
    r"イーサリアム|ETH",
    r"日銀|日本銀行",
    r"FRB|連邦準備",
    r"原油|WTI|ブレント",
    r"金相場|ゴールド",
    r"半導体",
    r"アサヒ(?:HD|グループ)?",
    r"トヨタ",
    r"ソニー",
    r"任天堂",
    r"エヌビディア|NVIDIA",
    r"テスラ|TSLA",
    r"決算",
    r"利上げ|利下げ",
    r"円安|円高",
]


class NewsCollector(Step):
    """Collect a broad candidate set, then select a diverse final set.

    The collector intentionally separates retrieval from editorial selection:
    providers fetch real candidate news first, then an injected LLM can rank those
    concrete candidates against recent topics. If the LLM is unavailable or its
    response violates the strict selection contract, a deterministic entity-aware
    fallback keeps the workflow usable without inventing news.
    """

    name = "collect_news"
    output_filename = "news.json"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        providers: List[Provider],
        llm_provider: Provider | None = None,
        query: str | None = None,
        query_buckets: Dict[str, str] | None = None,
        bucket_schedule: str | None = None,
        fetch_count: int = 9,
        final_count: int = 3,
        cooldown_hours: int = 24,
        recent_topics_runs: int = 5,
        recent_topics_max_chars: int = 500,
        **kwargs: Any,
    ):
        super().__init__(run_id, run_dir)
        self.providers = providers
        self.llm_provider = llm_provider
        self.query = (query or "").strip() or None
        self.query_buckets = query_buckets or {}
        self.bucket_schedule = bucket_schedule
        self.fetch_count = fetch_count
        self.final_count = final_count
        self.recent_topics_runs = recent_topics_runs
        self.recent_topics_max_chars = recent_topics_max_chars

    def execute(self, inputs: Dict[str, Path]) -> Path:
        tracker = AimTracker.get_instance(self.run_id)
        start = time.time()
        recent = gather_recent_topics(self.run_dir, self.run_id, self.recent_topics_runs)

        bucket_key, query = self._select_query()
        candidate_count = max(self.fetch_count, self.final_count * 3)
        logger.info("Selected retrieval query: %s -> %s", bucket_key, query)

        candidates = execute_with_fallback(
            self.providers,
            query=query,
            count=candidate_count,
            recent_topics_note="",
        )
        candidates = self._deduplicate_urls(candidates)
        logger.info("Fetched %s unique candidates", len(candidates))

        if len(candidates) < self.final_count:
            raise ValueError(
                f"Not enough unique news candidates: {len(candidates)} < {self.final_count}"
            )

        selected, selection_record = self.select_news(candidates, recent)
        if len(selected) != self.final_count:
            raise ValueError(
                f"News selection returned {len(selected)} items; expected {self.final_count}"
            )

        self._save_selection_record(selection_record)
        tracker.track_prompt(
            step_name="collect_news",
            template_name="news_selection",
            prompt=selection_record.get("prompt", query),
            inputs={
                "candidate_count": len(candidates),
                "recent_topics": self._recent_topics_note(recent),
                "selection_mode": selection_record.get("mode", "unknown"),
            },
            output=json.dumps(selection_record.get("selections", []), ensure_ascii=False),
            model=selection_record.get("model", "rule"),
            duration=time.time() - start,
        )
        return self._save(selected)

    def select_news(
        self, candidates: List[NewsItem], recent_topics: List[str]
    ) -> Tuple[List[NewsItem], Dict[str, Any]]:
        """Select final news from concrete candidates and return an audit record."""
        prompt = self._build_selection_prompt(candidates, recent_topics)
        provider = self.llm_provider

        if provider is not None and provider.is_available():
            try:
                raw = provider.execute(prompt=prompt)
                selections = self._parse_selection(raw, len(candidates))
                if len(selections) == self.final_count:
                    selected = [candidates[item["index"]] for item in selections]
                    return selected, self._selection_record(
                        candidates,
                        selections,
                        prompt=prompt,
                        raw_response=raw,
                        mode="llm",
                        model=getattr(provider, "model", getattr(provider, "name", "llm")),
                    )
                logger.warning(
                    "LLM selection contract violation: expected %s unique selections, got %s",
                    self.final_count,
                    len(selections),
                )
            except Exception as exc:  # noqa: BLE001 - selection must have safe fallback
                logger.warning("LLM news selection failed; using deterministic fallback: %s", exc)

        selected = self._diverse_fallback(candidates, recent_topics)
        fallback_selections = [
            {"index": candidates.index(item), "reason": "deterministic diversity fallback"}
            for item in selected
        ]
        return selected, self._selection_record(
            candidates,
            fallback_selections,
            prompt=prompt,
            raw_response=None,
            mode="fallback",
            model="rule",
        )

    def _build_selection_prompt(
        self, candidates: List[NewsItem], recent_topics: List[str]
    ) -> str:
        template = load_prompt_template("news_selection", self.run_id)
        candidate_payload = [
            {
                "index": idx,
                "title": item.title,
                "summary": item.summary,
                "url": item.url,
            }
            for idx, item in enumerate(candidates)
        ]
        return template.format(
            candidates=json.dumps(candidate_payload, ensure_ascii=False, indent=2),
            recent_topics_note=self._recent_topics_note(recent_topics),
            count=self.final_count,
        )

    def _parse_selection(self, raw: str, candidate_count: int) -> List[Dict[str, Any]]:
        candidate = extract_code_block(raw) or raw
        data = json.loads(candidate)
        entries = data.get("selections") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            raise ValueError("news_selection response must contain a selections list")

        parsed: List[Dict[str, Any]] = []
        seen: set[int] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            index = entry.get("index")
            reason = str(entry.get("reason") or "").strip()
            if isinstance(index, bool) or not isinstance(index, int):
                continue
            if not 0 <= index < candidate_count or index in seen or not reason:
                continue
            seen.add(index)
            parsed.append({"index": index, "reason": reason})
        return parsed[: self.final_count]

    def _selection_record(
        self,
        candidates: List[NewsItem],
        selections: List[Dict[str, Any]],
        *,
        prompt: str,
        raw_response: str | None,
        mode: str,
        model: str,
    ) -> Dict[str, Any]:
        return {
            "schema": "news-selection.v1",
            "mode": mode,
            "model": model,
            "candidates": [item.model_dump(mode="json") for item in candidates],
            "llm_response": raw_response,
            "selections": selections,
            "selected_news": [
                candidates[item["index"]].model_dump(mode="json") for item in selections
            ],
            "prompt": prompt,
        }

    def _save_selection_record(self, record: Dict[str, Any]) -> Path:
        path = self.run_dir / self.run_id / "news_selection.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _recent_topics_note(self, topics: List[str]) -> str:
        note = "\n".join(topics[-5:]).strip() or "直近テーマ情報なし"
        return note[: self.recent_topics_max_chars]

    def _select_query(self) -> Tuple[str, str]:
        if self.query:
            return "broad", self.query
        return self._select_bucket()

    def _select_bucket(self) -> Tuple[str, str]:
        """Retain bucket rotation as a backwards-compatible retrieval fallback."""
        if self.bucket_schedule and self.bucket_schedule in self.query_buckets:
            return self.bucket_schedule, self.query_buckets[self.bucket_schedule]
        if not self.query_buckets:
            raise ValueError("No news query or query buckets configured")

        recent = gather_recent_topics(self.run_dir, self.run_id, self.recent_topics_runs)
        saturated = self._get_saturated_entities(recent)
        bucket_keys = list(self.query_buckets.keys())
        start_idx = hash(self.run_id) % len(bucket_keys)

        for i in range(len(bucket_keys)):
            key = bucket_keys[(start_idx + i) % len(bucket_keys)]
            query = self.query_buckets[key]
            if not (self._extract_entities(query) & saturated):
                return key, query

        key = bucket_keys[start_idx]
        return key, self.query_buckets[key]

    def _diverse_fallback(
        self, candidates: List[NewsItem], recent_topics: List[str]
    ) -> List[NewsItem]:
        saturated = self._get_saturated_entities(recent_topics)
        selected: List[NewsItem] = []
        selected_entities: set[str] = set()

        def score(item: NewsItem) -> Tuple[int, int]:
            entities = self._extract_entities(item.title)
            recent_overlap = len(entities & saturated)
            selected_overlap = len(entities & selected_entities)
            return (recent_overlap + selected_overlap, selected_overlap)

        remaining = list(candidates)
        while remaining and len(selected) < self.final_count:
            best = min(enumerate(remaining), key=lambda pair: (score(pair[1]), pair[0]))
            item = remaining.pop(best[0])
            selected.append(item)
            selected_entities.update(self._extract_entities(item.title))
        return selected

    def _deduplicate_urls(self, items: List[NewsItem]) -> List[NewsItem]:
        result: List[NewsItem] = []
        seen_urls: set[str] = set()
        for item in items:
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            result.append(item)
        return result

    def _get_saturated_entities(self, topics: List[str]) -> set[str]:
        entities: set[str] = set()
        for topic in topics:
            entities.update(self._extract_entities(topic))
        return entities

    def _extract_entities(self, text: str) -> set[str]:
        entities: set[str] = set()
        for pattern in ENTITY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                entities.add(pattern.split("|")[0].split("(")[0])
        return entities

    def _save(self, items: List[NewsItem]) -> Path:
        path = self.get_output_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(
                [item.model_dump(mode="json") for item in items],
                handle,
                ensure_ascii=False,
                indent=2,
            )
        return path
