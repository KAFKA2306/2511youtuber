import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from src.core.step import Step
from src.models import NewsItem
from src.providers.base import Provider, execute_with_fallback
from src.tracking import AimTracker
from src.utils.history import gather_recent_topics
from src.utils.logger import get_logger

logger = get_logger(__name__)

class NewsCollector(Step):
    """
    Revised NewsCollector with Bucket & Filtering Logic.
    
    Strategy:
    1. Select a Query Bucket (rotate or schedule).
    2. Fetch many candidates (fetch_count=50).
    3. Normalize & Deduplicate (URL/Title).
    4. Apply Cooldown (exclude recent topics).
    5. Final Selection (pick top N).
    """
    name = "collect_news"
    output_filename = "news.json"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        providers: List[Provider],
        query: str = "", # Deprecated/Unused
        count: int = 3, # Deprecated (legacy)
        query_buckets: Dict[str, str] | None = None,
        bucket_schedule: str | None = None,
        fetch_count: int = 50,
        final_count: int = 3,
        cooldown_hours: int = 24,
        recent_topics_runs: int = 30, # Used for cooldown lookup
        recent_topics_max_chars: int = 2000,
        recent_topics_min_token_length: int = 2,
        recent_topics_stopwords: List[str] | None = None,
    ):
        super().__init__(run_id, run_dir)
        self.providers = providers
        # Config mapping
        self.query_buckets = query_buckets or {}
        self.bucket_schedule = bucket_schedule
        self.fetch_count = fetch_count
        self.final_count = final_count
        self.cooldown_hours = cooldown_hours
        self.recent_topics_runs = recent_topics_runs
        
        # Legacy fallback if buckets missing
        if not self.query_buckets:
            logger.warning("No query_buckets found. Falling back to legacy 'query' mode.")
            self.query_buckets = {"legacy": query}
            
    def execute(self, inputs: Dict[str, Path]) -> Path:
        tracker = AimTracker.get_instance(self.run_id)
        start_time = time.time()
        
        # 1. Bucket Selection
        bucket_key, bucket_query = self._select_bucket()
        logger.info(f"Selected News Bucket: {bucket_key} (Query: {bucket_query})")
        
        # 2. Fetch Candidates
        # Note: We pass empty recent_topics_note to provider because we handle dedupe ourselves now
        raw_candidates = execute_with_fallback(
            self.providers,
            query=bucket_query,
            count=self.fetch_count,
            recent_topics_note="", 
        )
        logger.info(f"Fetched {len(raw_candidates)} raw candidates.")

        # 3. Normalize & Cluster
        clusters = self._normalize_and_cluster(raw_candidates)
        logger.info(f"Formed {len(clusters)} unique clusters from raw items.")

        # 4. Apply Cooldown
        recent_topics = gather_recent_topics(self.run_dir, self.run_id, self.recent_topics_runs)
        allowed_clusters, rejection_log = self._apply_cooldown(clusters, recent_topics)
        logger.info(f"Cooldown passed: {len(allowed_clusters)}/{len(clusters)} clusters.")
        
        if not allowed_clusters:
            # Emergency Fallback: If all rejected, pick one from rejected that is oldest?
            # Or just raise error. The user said "If wiped out, no generation".
            # But to be safe for uptime, we might want to log strictly and fail.
            logger.error("All clusters rejected by cooldown logic! Rejection Log: " + str(rejection_log)[:1000])
            raise ValueError("News candidates exhausted by cooldown filter. Stopping generation.")

        # 5. Final Selection
        # Simple selection: Take top N from allowed.
        # Future improvement: smarter scoring.
        final_items = [c[0] for c in allowed_clusters[:self.final_count]] # c[0] is representative item
        
        # Track metadata
        duration = time.time() - start_time
        self._track_execution(tracker, bucket_key, bucket_query, raw_candidates, final_items, duration)

        # Save output
        return self._save_output(final_items)

    def _select_bucket(self) -> Tuple[str, str]:
        """
        Select a bucket. 
        Logic: Hash of run_id or random for simple rotation.
        User suggested: "Rotate".
        """
        if self.bucket_schedule and self.bucket_schedule in self.query_buckets:
            return self.bucket_schedule, self.query_buckets[self.bucket_schedule]
            
        keys = list(self.query_buckets.keys())
        # Use simple hash of run_id (timestamp string) to be deterministic for re-runs of same ID,
        # but changing for new runs.
        # run_id "20251222_180000" -> roughly changes every second
        # If we run 2x a day, we want different buckets.
        # Let's use random.choice for now as it ensures diversity over time distribution.
        selected_key = random.choice(keys)
        return selected_key, self.query_buckets[selected_key]

    def _normalize_and_cluster(self, candidates: List[NewsItem]) -> List[List[NewsItem]]:
        """
        Deduplicate by URL and Title Similarity.
        Returns list of clusters (each cluster is a list of NewsItems, representative first).
        """
        clusters: List[List[NewsItem]] = []
        
        for item in candidates:
            # 1. Exact URL Dedupe (Check if already in any cluster)
            if any(c[0].url == item.url for c in clusters):
                continue
                
            # 2. Title Similarity (Jaccard or substring)
            # Simple check: if title is very similar to existing cluster representative
            is_duplicate = False
            for cluster in clusters:
                rep = cluster[0]
                if self._calculate_similarity(item.title, rep.title) > 0.6:
                    cluster.append(item)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                clusters.append([item])
                
        return clusters

    def _apply_cooldown(self, clusters: List[List[NewsItem]], recent_topics: List[str]) -> Tuple[List[List[NewsItem]], List[str]]:
        """
        Filter out clusters that match recent topics.
        Returns: (allowed_clusters, log_of_rejections)
        """
        allowed = []
        log = []
        
        for cluster in clusters:
            rep = cluster[0]
            is_cool = True
            for past_topic in recent_topics:
                # Check similarity between candidate title and past topic title
                sim = self._calculate_similarity(rep.title, past_topic)
                if sim > 0.3: # Threshold for "Same Topic"
                    is_cool = False
                    log.append(f"Rejected '{rep.title}' vs Past '{past_topic}' (Sim: {sim:.2f})")
                    break
            
            if is_cool:
                allowed.append(cluster)
                
        return allowed, log

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Entity-based similarity for Japanese financial headlines.
        Extracts key financial entities and checks overlap.
        """
        if not text1 or not text2:
            return 0.0
        if text1 == text2:
            return 1.0
        
        entities1 = self._extract_entities(text1)
        entities2 = self._extract_entities(text2)
        
        if not entities1 or not entities2:
            return 0.0
            
        intersection = len(entities1 & entities2)
        union = len(entities1 | entities2)
        return intersection / union
    
    def _extract_entities(self, text: str) -> set:
        """
        Extract key financial entities from Japanese text.
        Returns a set of normalized entity strings.
        """
        import re
        entities = set()
        
        # Key financial indices and terms
        patterns = [
            r'日経平均',
            r'TOPIX',
            r'S&P500|S&P\s*500|エスアンドピー',
            r'NYダウ|ダウ平均',
            r'NASDAQ|ナスダック',
            r'ドル円|円ドル|USD/JPY',
            r'ビットコイン|BTC',
            r'イーサリアム|ETH',
            r'日銀|日本銀行',
            r'FRB|連邦準備',
            r'原油|WTI|ブレント',
            r'金相場|ゴールド',
            # Company patterns (simplified)
            r'アサヒ(?:HD|グループ|ホールディングス)?',
            r'トヨタ',
            r'ソニー',
            r'任天堂',
            r'エヌビディア|NVIDIA',
            r'テスラ|TSLA',
            # Event types
            r'決算',
            r'利上げ|利下げ',
            r'円安|円高',
            r'暴落|急落|急騰|高騰',
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Normalize the entity name
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities.add(pattern.split('|')[0].split('(?')[0])  # Use first variant as key
        
        return entities

    def _track_execution(self, tracker, bucket, query, raw, final, duration):
        tracker.track_prompt(
            step_name="collect_news",
            template_name="bucket_selection", 
            prompt=f"Bucket: {bucket}\nQuery: {query}",
            inputs={"bucket": bucket},
            output=json.dumps([{"title": i.title} for i in final], ensure_ascii=False),
            model="heuristic",
            duration=duration,
        )

    def _save_output(self, items: List[NewsItem]) -> Path:
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([item.model_dump(mode="json") for item in items], f, ensure_ascii=False, indent=2)
        return output_path
