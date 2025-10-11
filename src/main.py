import sys
from datetime import datetime
from pathlib import Path

from src.steps.audio import AudioSynthesizer
from src.steps.metadata import MetadataAnalyzer
from src.steps.news import NewsCollector
from src.steps.script import ScriptGenerator
from src.steps.subtitle import SubtitleFormatter
from src.steps.thumbnail import ThumbnailGenerator
from src.steps.video import VideoRenderer
from src.steps.youtube import YouTubeUploader
from src.utils.config import Config
from src.utils.logger import get_logger
from src.workflow import WorkflowOrchestrator

logger = get_logger(__name__)


def create_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def estimate_max_chars_per_line(
    resolution: str, width_per_char_pixels: int, min_visual_width: int, max_visual_width: int
) -> int:
    width_part = resolution.lower().split("x", 1)[0].strip()
    width = int(width_part)
    base = int(width / width_per_char_pixels)
    return max(min_visual_width, min(max_visual_width, base))


def main():
    logger.info("Starting YouTube AI Video Generator v2")

    config = Config.load()

    run_id = create_run_id()
    run_dir = Path(config.workflow.default_run_dir)

    logger.info("Initializing workflow run_id=%s", run_id)

    steps = [
        NewsCollector(
            run_id=run_id,
            run_dir=run_dir,
            query=config.steps.news.query,
            count=config.steps.news.count,
            providers_config=config.providers.news,
        ),
        ScriptGenerator(run_id=run_id, run_dir=run_dir, speakers_config=config.steps.script.speakers),
        AudioSynthesizer(
            run_id=run_id,
            run_dir=run_dir,
            voicevox_config={
                "url": config.providers.tts.voicevox.url,
                "speakers": dict(config.providers.tts.voicevox.speakers),
                "manager_script": config.providers.tts.voicevox.manager_script,
                "auto_start": config.providers.tts.voicevox.auto_start,
            },
            speaker_aliases={
                profile.name: profile.aliases
                for profile in (
                    config.steps.script.speakers.analyst,
                    config.steps.script.speakers.reporter,
                    config.steps.script.speakers.narrator,
                )
            },
        ),
        SubtitleFormatter(
            run_id=run_id,
            run_dir=run_dir,
            max_chars_per_line=estimate_max_chars_per_line(
                config.steps.video.resolution,
                config.steps.subtitle.width_per_char_pixels,
                config.steps.subtitle.min_visual_width,
                config.steps.subtitle.max_visual_width,
            ),
        ),
        VideoRenderer(
            run_id=run_id,
            run_dir=run_dir,
            video_config={
                "resolution": config.steps.video.resolution,
                "fps": config.steps.video.fps,
                "codec": config.steps.video.codec,
                "preset": config.steps.video.preset,
                "crf": config.steps.video.crf,
                "effects": [effect.model_dump() for effect in config.steps.video.effects],
            },
        ),
    ]

    metadata_config = config.steps.metadata.model_dump()
    if metadata_config.get("enabled", False):
        steps.append(MetadataAnalyzer(run_id=run_id, run_dir=run_dir, metadata_config=metadata_config))

    if config.steps.thumbnail.enabled:
        steps.append(
            ThumbnailGenerator(run_id=run_id, run_dir=run_dir, thumbnail_config=config.steps.thumbnail.model_dump())
        )

    if config.steps.youtube.enabled and metadata_config.get("enabled", False):
        steps.append(YouTubeUploader(run_id=run_id, run_dir=run_dir, youtube_config=config.steps.youtube.model_dump()))

    orchestrator = WorkflowOrchestrator(run_id=run_id, steps=steps, run_dir=run_dir)

    result = orchestrator.execute()

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
    elif result.status == "partial":
        print("\n⚠️  Workflow completed with errors")
        print(f"Run ID: {run_id}")
        print(f"Completed steps: {len(result.outputs)}/{len(steps)}")
        print(f"Errors: {result.errors}")
        return 1
    else:
        print("\n❌ Workflow failed")
        print(f"Run ID: {run_id}")
        print(f"Errors: {result.errors}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
