from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Mapping

from feedgen.feed import FeedGenerator

from src.core.step import Step
from src.utils.config import PodcastStepConfig


class PodcastExporter(Step):
    name = "export_podcast"
    output_filename = "podcast.xml"
    is_required = False

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        podcast_config: PodcastStepConfig | Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(run_id, run_dir)
        self.config: PodcastStepConfig
        config_data = podcast_config if isinstance(podcast_config, PodcastStepConfig) else podcast_config or {}
        self.config = PodcastStepConfig.model_validate(config_data)

    def execute(self, inputs: Dict[str, Path]) -> Path:
        audio_path = Path(inputs["synthesize_audio"])

        output_path = self.get_output_path()
        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        audio_dest = output_dir / "podcast_audio.wav"
        shutil.copy(audio_path, audio_dest)

        fg = FeedGenerator()
        fg.load_extension("podcast")

        cfg = self.config
        feed_id = f"{cfg.feed_url.rstrip('/')}/{self.run_id}"
        fg.id(feed_id)
        fg.title(cfg.feed_title)
        fg.description(cfg.feed_description)
        fg.author({"name": cfg.feed_author})
        fg.link(href=cfg.feed_url, rel="alternate")
        fg.language("ja")

        fe = fg.add_entry()
        fe.id(feed_id)
        fe.title(f"Episode {self.run_id}")
        fe.description(f"Run ID: {self.run_id}")
        fe.enclosure(str(audio_dest), 0, "audio/wav")
        fe.published(datetime.now(timezone.utc))

        fg.rss_file(str(output_path))

        return output_path
