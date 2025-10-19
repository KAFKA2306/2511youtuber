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
from src.steps.twitter import TwitterPoster
from src.steps.video import VideoRenderer
from src.steps.youtube import YouTubeUploader
from src.steps.intro_outro import IntroOutroConcatenator
from src.providers.twitter import TwitterClient
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
    audio_cfg = config.steps.audio
    metadata_cfg = config.steps.metadata.model_dump()
    voicevox_config = voicevox_cfg.model_dump()
    voicevox_config["speakers"] = dict(voicevox_config.get("speakers", {}))
    voicevox_config.pop("enabled", None)
    video_config = video_cfg.model_dump()
    video_config["effects"] = [effect.model_dump() for effect in video_cfg.effects]
    subtitle_style = video_cfg.subtitles
    margin_l = subtitle_style.margin_l if subtitle_style else 0
    margin_r = subtitle_style.margin_r if subtitle_style else 0
    wrap_width_pixels = SubtitleFormatter.safe_pixel_width(video_cfg.resolution, margin_l, margin_r)
    font_path = subtitle_style.font_path if subtitle_style else None
    font_size = subtitle_style.font_size if subtitle_style else None
    resolution_values = video_cfg.resolution.lower().split('x')
    video_width = int(resolution_values[0])
    video_height = int(resolution_values[1])

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

    steps.append(
        VideoRenderer(
            run_id=run_id,
            run_dir=run_dir,
            video_config=video_config,
        )
    )

    intro_cfg = video_cfg.intro_outro
    if intro_cfg and intro_cfg.enabled:
        steps.append(
            IntroOutroConcatenator(
                run_id=run_id,
                run_dir=run_dir,
                intro_path=intro_cfg.intro_path,
                outro_path=intro_cfg.outro_path,
                codec=video_cfg.codec,
                preset=video_cfg.preset,
                crf=video_cfg.crf,
                thumbnail_overlay=video_config.get("thumbnail_overlay"),
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
            twitter_cfg = config.steps.twitter
            client = TwitterClient.from_env(dry_run=twitter_cfg.dry_run)
            steps.append(
                TwitterPoster(
                    run_id=run_id,
                    run_dir=run_dir,
                    client=client,
                    clip_duration=twitter_cfg.clip_duration_seconds,
                    start_offset_seconds=twitter_cfg.start_offset_seconds,
                    outro_path=intro_cfg.twitter_outro_path if intro_cfg else None,
                    codec=video_cfg.codec,
                    preset=video_cfg.preset,
                    crf=video_cfg.crf,
                    width=video_width,
                    height=video_height,
                    fps=video_cfg.fps,
                    sample_rate=audio_cfg.sample_rate,
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


def _speaker_aliases(speakers) -> dict[str, List[str]]:
    profiles = (speakers.analyst, speakers.reporter, speakers.narrator)
    return {profile.name: profile.aliases for profile in profiles}
