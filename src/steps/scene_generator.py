from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List

from src.core.io_utils import load_json
from src.core.step import Step
from src.services.image_generation import (
    ImageGenerationRequest,
    ImageGenerationService,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# DOMAIN MODELS
# ============================================================


class SceneType(str, Enum):
    """Types of scene images to generate."""

    LITERAL = "literal"  # News context: charts, financial districts, trading floors
    ABSTRACT = "abstract"  # Mood/sentiment: stormy ocean, golden sunrise, geometric patterns
    ATMOSPHERIC = "atmospheric"  # Background optimized: soft bokeh, blurred city lights


@dataclass
class SceneVariant:
    """Represents a single generated scene image variant."""

    scene_index: int
    scene_type: SceneType
    variant_index: int
    timestamp: float
    image_path: Path
    prompt: str
    seed: int
    mood: str
    segment_indices: List[int]


@dataclass
class SceneContext:
    """Rich context for scene generation."""

    title: str
    description: str
    segments: List[Dict]
    news_keywords: List[str]
    market_sentiment: str  # bull, bear, neutral
    top_entities: List[str]


# ============================================================
# SERVICE LAYER
# ============================================================


class ContextExtractor:
    """Extracts rich context from news and stats data."""

    @staticmethod
    def extract_news_keywords(news_data: Dict | List) -> List[str]:
        """Extract top keywords from news items.

        Handles both formats:
        - Old: list of news items directly
        - New: dict with "news_items" key
        """
        keywords = []

        # Handle both old (list) and new (dict) formats
        if isinstance(news_data, list):
            news_items = news_data
        elif isinstance(news_data, dict):
            news_items = news_data.get("news_items", [])
        else:
            return []

        for item in news_items[:3]:  # Top 3 news
            title = item.get("title", "")
            # Simple keyword extraction (can be enhanced with NLP)
            words = title.split()
            keywords.extend([w for w in words if len(w) > 3])

        return list(set(keywords))[:10]  # Top 10 unique keywords

    @staticmethod
    def extract_market_sentiment(stats_data: Dict | None) -> str:
        """Extract market sentiment from stats (bull/bear/neutral)."""
        if not stats_data:
            return "neutral"

        # Simple heuristic: check for positive/negative keywords
        stats_text = json.dumps(stats_data).lower()

        positive_signals = ["上昇", "増加", "好調", "最高", "記録"]
        negative_signals = ["下落", "減少", "懸念", "リスク", "警告"]

        pos_count = sum(1 for sig in positive_signals if sig in stats_text)
        neg_count = sum(1 for sig in negative_signals if sig in stats_text)

        if pos_count > neg_count:
            return "bull"
        elif neg_count > pos_count:
            return "bear"
        return "neutral"


class PromptBuilder:
    """Builds YouTube-optimized prompts using config-based templates."""

    def __init__(self, scene_prompts_config: Dict):
        self.config = scene_prompts_config
        self.common = scene_prompts_config.get("common", {})
        self.types = (
            scene_prompts_config.get("literal", {}),
            scene_prompts_config.get("abstract", {}),
            scene_prompts_config.get("atmospheric", {}),
        )
        self.boosters = scene_prompts_config.get("youtube_boosters", [])

    def build_literal_prompt(
        self,
        context: SceneContext,
        segment_text: str,
        mood: str,
    ) -> Dict[str, str]:
        """Build prompt for literal/news-context scene."""
        import random

        literal_config = self.config.get("literal", {})

        # Randomly select core element
        core_elements = literal_config.get("core_elements", [])
        core = random.choice(core_elements) if core_elements else "modern financial district"

        # Get mood modifiers
        mood_mods = literal_config.get("mood_modifiers", {}).get(mood, {})
        lighting = mood_mods.get("lighting", "")
        atmosphere = mood_mods.get("atmosphere", "")
        color = mood_mods.get("color", "")

        # Randomly select YouTube booster
        booster = random.choice(self.boosters) if self.boosters else ""

        # Get quality baseline
        quality = self.common.get("quality", "")
        youtube_appeal = self.common.get("youtube_appeal", "")

        # Randomly select composition technique
        composition_techniques = self.common.get("composition_techniques", [])
        composition = random.choice(composition_techniques) if composition_techniques else ""

        # Construct prompt
        prompt_parts = [core, lighting, atmosphere, color, composition, booster, youtube_appeal, quality]
        final_prompt = ", ".join([p for p in prompt_parts if p])

        # Get negative prompt
        negative_base = self.common.get("negative_base", "")
        negative_extra = literal_config.get("negative_extra", "")
        negative_prompt = f"{negative_base}, {negative_extra}"

        return {
            "prompt": final_prompt,
            "negative_prompt": negative_prompt,
        }

    def build_abstract_prompt(
        self,
        context: SceneContext,
        segment_text: str,
        mood: str,
    ) -> Dict[str, str]:
        """Build prompt for abstract/mood scene."""
        import random

        abstract_config = self.config.get("abstract", {})

        # Randomly select core element
        core_elements = abstract_config.get("core_elements", [])
        core = random.choice(core_elements) if core_elements else "flowing abstract patterns"

        # Get mood modifiers
        mood_mods = abstract_config.get("mood_modifiers", {}).get(mood, {})
        atmosphere = mood_mods.get("atmosphere", "")
        color = mood_mods.get("color", "")
        motion = mood_mods.get("motion", "")

        # Randomly select YouTube booster
        booster = random.choice(self.boosters) if self.boosters else ""

        # Get quality baseline
        quality = self.common.get("quality", "")
        youtube_appeal = self.common.get("youtube_appeal", "")

        # Randomly select composition technique
        composition_techniques = self.common.get("composition_techniques", [])
        composition = random.choice(composition_techniques) if composition_techniques else ""

        # Construct prompt
        prompt_parts = [core, atmosphere, color, motion, composition, booster, youtube_appeal, quality]
        final_prompt = ", ".join([p for p in prompt_parts if p])

        # Get negative prompt
        negative_base = self.common.get("negative_base", "")
        negative_extra = abstract_config.get("negative_extra", "")
        negative_prompt = f"{negative_base}, {negative_extra}"

        return {
            "prompt": final_prompt,
            "negative_prompt": negative_prompt,
        }

    def build_atmospheric_prompt(
        self,
        context: SceneContext,
        mood: str,
    ) -> Dict[str, str]:
        """Build prompt for atmospheric/background scene."""
        import random

        atmos_config = self.config.get("atmospheric", {})

        # Randomly select core element
        core_elements = atmos_config.get("core_elements", [])
        core = random.choice(core_elements) if core_elements else "soft bokeh background"

        # Get mood modifiers
        mood_mods = atmos_config.get("mood_modifiers", {}).get(mood, {})
        color = mood_mods.get("color", "")
        effect = mood_mods.get("effect", "")

        # Randomly select YouTube booster
        booster = random.choice(self.boosters) if self.boosters else ""

        # Get quality baseline
        quality = self.common.get("quality", "")
        youtube_appeal = self.common.get("youtube_appeal", "")

        # Randomly select composition technique
        composition_techniques = self.common.get("composition_techniques", [])
        composition = random.choice(composition_techniques) if composition_techniques else ""

        # Construct prompt
        prompt_parts = [core, color, effect, composition, booster, youtube_appeal, quality]
        final_prompt = ", ".join([p for p in prompt_parts if p])

        # Get negative prompt
        negative_base = self.common.get("negative_base", "")
        negative_extra = atmos_config.get("negative_extra", "")
        negative_prompt = f"{negative_base}, {negative_extra}"

        return {
            "prompt": final_prompt,
            "negative_prompt": negative_prompt,
        }


# ============================================================
# MAIN STEP
# ============================================================


class SceneGenerator(Step):
    """
    Generate atmospheric scene images for video backgrounds using Z-Image-Turbo.

    Implements Mass Generation Strategy:
    - Generates multiple variants per scene (Literal, Abstract, Atmospheric)
    - Uses rich context from news, stats, and script
    - Outputs 16:9 images optimized for YouTube
    """

    name = "generate_scenes"
    output_filename = "scene_manifest.json"
    is_required = False

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        image_service: ImageGenerationService,
        scene_config: Dict | None = None,
        prompts_config: Dict | None = None,
    ):
        super().__init__(run_id, run_dir)
        self.scene_config = scene_config or {}
        self.prompts_config = prompts_config or {}
        self.image_service = image_service

        self.enabled = bool(self.scene_config.get("enabled", False))
        self.images_per_video = int(self.scene_config.get("images_per_video", 4))
        self.variants_per_type = int(self.scene_config.get("variants_per_type", 2))
        self.width = int(self.scene_config.get("width", 1280))
        self.height = int(self.scene_config.get("height", 720))
        self.num_steps = int(self.scene_config.get("num_steps", 9))
        self.scene_duration_seconds = float(self.scene_config.get("scene_duration_seconds", 30.0))
        self.batch_size = int(self.scene_config.get("batch_size", 1))
        self.compile_model = bool(self.scene_config.get("compile_model", False))

    def execute(self, inputs: Dict[str, Path | str]) -> Path:
        output_dir = self.get_output_path().parent
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.get_output_path()

        if not self.enabled:
            output_path.write_text(json.dumps({"scenes": []}, ensure_ascii=False, indent=2))
            return output_path

        # Load inputs
        script_data = load_json(Path(inputs["generate_script"]))
        metadata = load_json(Path(inputs.get("analyze_metadata", ""))) if inputs.get("analyze_metadata") else None
        news_data = load_json(Path(inputs.get("collect_news", ""))) if inputs.get("collect_news") else None
        stats_data = None  # TODO: Add stats step if needed

        segments = script_data.get("segments", [])
        if not segments:
            logger.warning("No script segments found, skipping scene generation")
            output_path.write_text(json.dumps({"scenes": []}, ensure_ascii=False, indent=2))
            return output_path

        # Build rich context
        context = SceneContext(
            title=metadata.get("title", "") if metadata else "",
            description=metadata.get("description", "") if metadata else "",
            segments=segments,
            news_keywords=ContextExtractor.extract_news_keywords(news_data) if news_data else [],
            market_sentiment=ContextExtractor.extract_market_sentiment(stats_data),
            top_entities=self._extract_entities(" ".join([s.get("text", "") for s in segments[:5]])),
        )

        # Generate scenes
        variants = self._generate_all_variants(context, output_dir)

        # Build manifest
        manifest = {
            "scenes": [self._variant_to_dict(v) for v in variants],
            "config": {
                "images_per_video": self.images_per_video,
                "variants_per_type": self.variants_per_type,
                "scene_duration_seconds": self.scene_duration_seconds,
                "width": self.width,
                "height": self.height,
            },
        }

        output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        logger.info(f"Generated {len(variants)} scene image variants")

        return output_path

    def _generate_all_variants(
        self,
        context: SceneContext,
        output_dir: Path,
    ) -> List[SceneVariant]:
        """Generate all scene variants using batch processing."""
        total_duration = self._calculate_total_duration(context.segments)
        scene_timestamps = self._calculate_scene_timestamps(total_duration)

        # Load scene-specific prompts config
        import yaml

        scene_prompts_path = Path("config/scene_prompts.yaml")
        with open(scene_prompts_path, "r", encoding="utf-8") as f:
            scene_prompts_config = yaml.safe_load(f)

        prompt_builder = PromptBuilder(scene_prompts_config)

        # Phase 1: Prepare all requests and metadata
        requests = []
        variants = []

        for scene_idx, timestamp in enumerate(scene_timestamps):
            # Create scene directory
            scene_dir = output_dir / f"scene_{scene_idx:02d}"
            scene_dir.mkdir(exist_ok=True)

            # Get relevant segments
            segment_group = self._get_segments_for_timestamp(context.segments, timestamp, self.scene_duration_seconds)
            segment_text = " ".join([s.get("text", "") for s in segment_group])[:500]
            segment_indices = [s.get("index", i) for i, s in enumerate(segment_group)]

            # Detect mood
            mood = self._detect_mood(segment_text, segment_group)

            # Prepare variants for each type
            for scene_type in SceneType:
                for variant_idx in range(self.variants_per_type):
                    request, variant = self._prepare_variant_metadata(
                        scene_idx=scene_idx,
                        scene_type=scene_type,
                        variant_idx=variant_idx,
                        timestamp=timestamp,
                        context=context,
                        segment_text=segment_text,
                        segment_indices=segment_indices,
                        mood=mood,
                        prompt_builder=prompt_builder,
                        scene_dir=scene_dir,
                    )
                    requests.append(request)
                    variants.append(variant)

        # Phase 2: Generate all images in batches
        logger.info(f"Generating {len(requests)} images with batch_size={self.batch_size}...")
        results = self.image_service.generate_batch(requests)

        # Phase 3: Save images and update variants
        for variant, result in zip(variants, results):
            result.image.save(variant.image_path)
            logger.info(
                f"Saved scene {variant.scene_index + 1}/{len(scene_timestamps)} "
                f"[{variant.scene_type.value}] variant {variant.variant_index + 1}/{self.variants_per_type} "
                f"to {variant.image_path}"
            )

        return variants

    def _prepare_variant_metadata(
        self,
        scene_idx: int,
        scene_type: SceneType,
        variant_idx: int,
        timestamp: float,
        context: SceneContext,
        segment_text: str,
        segment_indices: List[int],
        mood: str,
        prompt_builder: PromptBuilder,
        scene_dir: Path,
    ) -> tuple[ImageGenerationRequest, SceneVariant]:
        """Prepare metadata for a scene variant (without generating image)."""
        # Build prompt based on type
        if scene_type == SceneType.LITERAL:
            prompt_data = prompt_builder.build_literal_prompt(context, segment_text, mood)
        elif scene_type == SceneType.ABSTRACT:
            prompt_data = prompt_builder.build_abstract_prompt(context, segment_text, mood)
        else:  # ATMOSPHERIC
            prompt_data = prompt_builder.build_atmospheric_prompt(context, mood)

        # Prepare generation request
        seed = 42 + scene_idx * 100 + variant_idx
        image_path = scene_dir / f"{scene_type.value}_{variant_idx:02d}.png"

        request = ImageGenerationRequest(
            prompt=prompt_data["prompt"],
            negative_prompt=prompt_data.get("negative_prompt", ""),
            width=self.width,
            height=self.height,
            num_inference_steps=self.num_steps,
            guidance_scale=0.0,
            seed=seed,
        )

        variant = SceneVariant(
            scene_index=scene_idx,
            scene_type=scene_type,
            variant_index=variant_idx,
            timestamp=timestamp,
            image_path=image_path,
            prompt=prompt_data["prompt"],
            seed=seed,
            mood=mood,
            segment_indices=segment_indices,
        )

        return request, variant

    def _calculate_total_duration(self, segments: List[Dict]) -> float:
        """Calculate total duration from segments."""
        total = 0.0
        for seg in segments:
            text = seg.get("text", "")
            chars = len(text)
            estimated_seconds = chars / 15.0
            total += estimated_seconds
        return total

    def _calculate_scene_timestamps(self, total_duration: float) -> List[float]:
        """Calculate evenly distributed scene timestamps."""
        if self.images_per_video <= 1:
            return [0.0]

        interval = total_duration / self.images_per_video
        return [i * interval for i in range(self.images_per_video)]

    def _get_segments_for_timestamp(
        self,
        segments: List[Dict],
        timestamp: float,
        window_seconds: float,
    ) -> List[Dict]:
        """Get segments within a time window around timestamp."""
        current_time = 0.0
        result = []

        for idx, seg in enumerate(segments):
            text = seg.get("text", "")
            duration = len(text) / 15.0
            seg_end = current_time + duration

            if current_time <= timestamp + window_seconds / 2 and seg_end >= timestamp - window_seconds / 2:
                result.append({"index": idx, **seg})

            current_time = seg_end

        return result if result else segments[:3]

    def _detect_mood(self, text: str, segments: List[Dict]) -> str:
        """Detect emotional mood from text."""
        crisis_keywords = ["下落", "暴落", "危機", "リスク", "警告", "懸念", "減少"]
        opportunity_keywords = ["上昇", "成長", "最高", "記録", "達成", "増加", "好調"]

        text_lower = text.lower()

        crisis_count = sum(1 for kw in crisis_keywords if kw in text_lower)
        opportunity_count = sum(1 for kw in opportunity_keywords if kw in text_lower)

        if crisis_count > opportunity_count:
            return "crisis"
        elif opportunity_count > crisis_count:
            return "opportunity"
        return "neutral"

    def _extract_entities(self, text: str) -> List[str]:
        """Extract key entities from text."""
        entities = []

        common_entities = [
            "Apple",
            "Google",
            "Microsoft",
            "Amazon",
            "Tesla",
            "日経平均",
            "S&P500",
            "NASDAQ",
            "ドル円",
            "ビットコイン",
            "FRB",
            "日銀",
            "ECB",
        ]

        for entity in common_entities:
            if entity in text:
                entities.append(entity)

        return entities[:5]

    @staticmethod
    def _variant_to_dict(variant: SceneVariant) -> Dict:
        """Convert SceneVariant to dict for JSON serialization."""
        return {
            "scene_index": variant.scene_index,
            "scene_type": variant.scene_type.value,
            "variant_index": variant.variant_index,
            "timestamp": variant.timestamp,
            "image_path": str(variant.image_path),
            "prompt": variant.prompt,
            "seed": variant.seed,
            "mood": variant.mood,
            "segment_indices": variant.segment_indices,
        }
