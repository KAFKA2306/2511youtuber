from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from src.core.orchestrator import WorkflowOrchestrator
from src.steps.audio import AudioSynthesizer
from src.steps.buzzsprout import BuzzsproutUploader
from src.steps.metadata import MetadataAnalyzer
from src.steps.news import NewsCollector
from src.steps.podcast import PodcastExporter
from src.steps.script import ScriptGenerator
from src.steps.subtitle import SubtitleFormatter
from src.steps.thumbnail import ThumbnailGenerator
from src.steps.video import VideoRenderer
from src.steps.twitter import TwitterPoster
from src.steps.youtube import YouTubeUploader
from src.utils.config import Config
from src.utils.discord import post_run_summary
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run(*, news_query: str | None = None) -> int:
    logger.info("Starting YouTube AI Video Generator v2")
    config = Config.load()
    if news_query:
        config.steps.news.query = news_query

    run_id = _create_run_id()
    run_dir = Path(config.workflow.default_run_dir)
    logger.info("Initializing workflow run_id=%s", run_id)

    steps = _build_steps(config, run_id, run_dir)
    orchestrator = WorkflowOrchestrator(run_id=run_id, steps=steps, run_dir=run_dir)

    try:
        result = orchestrator.execute()
    finally:
        if "collect_news" in orchestrator.state.outputs:
            post_run_summary(run_id, orchestrator.state.outputs)

    logger.info(
        "Workflow finished status=%s duration_seconds=%.2f outputs=%s errors=%s",
        result.status,
        result.duration_seconds,
        result.outputs,
        result.errors,
    )

    if result.status == "success":
        print("\n✅ Video generation completed successfully!")
        print(f"Run ID: {run_id}")
        print(f"Video: {result.outputs.get('render_video', 'N/A')}")
        print(f"Duration: {result.duration_seconds:.1f} seconds")
        return 0
    if result.status == "partial":
        print("\n⚠️  Workflow completed with errors")
        print(f"Run ID: {run_id}")
        print(f"Completed steps: {len(result.outputs)}/{len(steps)}")
        print(f"Errors: {result.errors}")
        return 1
    print("\n❌ Workflow failed")
    print(f"Run ID: {run_id}")
    print(f"Errors: {result.errors}")
    return 1


def _build_steps(config: Config, run_id: str, run_dir: Path) -> List:
    news_cfg = config.steps.news
    script_cfg = config.steps.script
    voicevox_cfg = config.providers.tts.voicevox
    subtitle_cfg = config.steps.subtitle
    video_cfg = config.steps.video
    metadata_cfg = config.steps.metadata.model_dump()
    voicevox_config = voicevox_cfg.model_dump()
    voicevox_config["speakers"] = dict(voicevox_config.get("speakers", {}))
    voicevox_config.pop("enabled", None)
    video_config = video_cfg.model_dump()
    video_config["effects"] = [effect.model_dump() for effect in video_cfg.effects]

    steps: List = [
        NewsCollector(
            run_id=run_id,
            run_dir=run_dir,
            query=news_cfg.query,
            count=news_cfg.count,
            providers_config=config.providers.news,
        ),
        ScriptGenerator(run_id=run_id, run_dir=run_dir, speakers_config=script_cfg.speakers),
        AudioSynthesizer(
            run_id=run_id,
            run_dir=run_dir,
            voicevox_config=voicevox_config,
            speaker_aliases=_speaker_aliases(script_cfg.speakers),
        ),
        SubtitleFormatter(
            run_id=run_id,
            run_dir=run_dir,
            max_chars_per_line=_estimate_max_chars_per_line(
                video_cfg.resolution,
                subtitle_cfg.width_per_char_pixels,
                subtitle_cfg.min_visual_width,
                subtitle_cfg.max_visual_width,
            ),
        ),
        VideoRenderer(
            run_id=run_id,
            run_dir=run_dir,
            video_config=video_config,
        ),
    ]

    if metadata_cfg.get("enabled", False):
        steps.append(MetadataAnalyzer(run_id=run_id, run_dir=run_dir, metadata_config=metadata_cfg))

    if config.steps.thumbnail.enabled:
        steps.append(
            ThumbnailGenerator(
                run_id=run_id,
                run_dir=run_dir,
                thumbnail_config=config.steps.thumbnail.model_dump(),
            )
        )

    if config.steps.youtube.enabled and metadata_cfg.get("enabled", False):
        steps.append(
            YouTubeUploader(
                run_id=run_id,
                run_dir=run_dir,
                youtube_config=config.steps.youtube.model_dump(),
            )
        )
        if config.steps.twitter.enabled:
            steps.append(
                TwitterPoster(
                    run_id=run_id,
                    run_dir=run_dir,
                    twitter_config=config.steps.twitter.model_dump(),
                )
            )

    if config.steps.podcast.enabled:
        steps.append(
            PodcastExporter(
                run_id=run_id,
                run_dir=run_dir,
                podcast_config=config.steps.podcast.model_dump(),
            )
        )

    if config.steps.buzzsprout.enabled:
        steps.append(
            BuzzsproutUploader(
                run_id=run_id,
                run_dir=run_dir,
                buzzsprout_config=config.steps.buzzsprout.model_dump(),
            )
        )

    return steps


def _create_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _estimate_max_chars_per_line(
    resolution: str, width_per_char_pixels: int, min_visual_width: int, max_visual_width: int
) -> int:
    width = int(resolution.lower().split("x", 1)[0].strip())
    base = int(width / width_per_char_pixels)
    return max(min_visual_width, min(max_visual_width, base))


def _speaker_aliases(speakers) -> dict[str, List[str]]:
    profiles = (speakers.analyst, speakers.reporter, speakers.narrator)
    return {profile.name: profile.aliases for profile in profiles}
