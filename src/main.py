import sys
from pathlib import Path
from datetime import datetime
from src.workflow import WorkflowOrchestrator
from src.steps.news import NewsCollector
from src.steps.script import ScriptGenerator
from src.steps.audio import AudioSynthesizer
from src.steps.subtitle import SubtitleFormatter
from src.steps.video import VideoRenderer
from src.utils.config import Config
from src.utils.logger import get_logger


logger = get_logger(__name__)


def create_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    logger.info("Starting YouTube AI Video Generator v2")

    config = Config.load()

    run_id = create_run_id()
    run_dir = Path(config.workflow.default_run_dir)

    logger.info(f"Initializing workflow", run_id=run_id)

    steps = [
        NewsCollector(
            run_id=run_id,
            run_dir=run_dir,
            query=config.steps.news.query,
            count=config.steps.news.count
        ),
        ScriptGenerator(
            run_id=run_id,
            run_dir=run_dir
        ),
        AudioSynthesizer(
            run_id=run_id,
            run_dir=run_dir,
            voicevox_config={
                "url": config.providers.tts.voicevox.url,
                "speakers": config.providers.tts.voicevox.speakers
            },
            pyttsx3_config={
                "speakers": {
                    k: v.model_dump() for k, v in config.providers.tts.pyttsx3.speakers.items()
                }
            }
        ),
        SubtitleFormatter(
            run_id=run_id,
            run_dir=run_dir
        ),
        VideoRenderer(
            run_id=run_id,
            run_dir=run_dir,
            video_config={
                "resolution": config.steps.video.resolution,
                "fps": config.steps.video.fps,
                "codec": config.steps.video.codec,
                "preset": config.steps.video.preset,
                "crf": config.steps.video.crf
            }
        )
    ]

    orchestrator = WorkflowOrchestrator(run_id=run_id, steps=steps, run_dir=run_dir)

    result = orchestrator.execute()

    logger.info(
        f"Workflow finished",
        status=result.status,
        duration_seconds=result.duration_seconds,
        outputs=result.outputs,
        errors=result.errors
    )

    if result.status == "success":
        print(f"\n✅ Video generation completed successfully!")
        print(f"Run ID: {run_id}")
        print(f"Video: {result.outputs.get('render_video', 'N/A')}")
        print(f"Duration: {result.duration_seconds:.1f} seconds")
        return 0
    elif result.status == "partial":
        print(f"\n⚠️  Workflow completed with errors")
        print(f"Run ID: {run_id}")
        print(f"Completed steps: {len(result.outputs)}/5")
        print(f"Errors: {result.errors}")
        return 1
    else:
        print(f"\n❌ Workflow failed")
        print(f"Run ID: {run_id}")
        print(f"Errors: {result.errors}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
