from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict

from src.core.io_utils import load_json, load_script
from src.core.step import Step
from src.providers.cloudflare_ai import CloudflareAIClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AIThumbnailGenerator(Step):
    name = "generate_thumbnail_ai"
    output_filename = "thumbnail_ai.png"
    is_required = False

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        ai_thumbnail_config: Dict | None = None,
    ) -> None:
        super().__init__(run_id, run_dir)
        cfg = dict(ai_thumbnail_config or {})
        self.enabled = bool(cfg.get("enabled", False))
        self.width = int(cfg.get("width", 1920))
        self.height = int(cfg.get("height", 1080))
        self.num_steps = int(cfg.get("num_steps", 6))

    def execute(self, inputs: Dict[str, Path | str]) -> Path:
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.enabled:
            output_path.touch(exist_ok=True)
            return output_path

        script = load_script(Path(inputs["generate_script"]))
        metadata = load_json(Path(inputs["analyze_metadata"])) if inputs.get("analyze_metadata") else None

        video_id = self.run_id
        title = self._resolve_title(metadata, script)
        description = str(metadata.get("description", "")).strip() if metadata else ""
        tags = ", ".join(metadata.get("tags", [])) if metadata else ""
        prompt = self._build_prompt(title, description, tags)
        seed = self._generate_seed(video_id)

        from src.utils.config import load_prompts

        prompts = load_prompts()
        negative_prompt = prompts.get("thumbnail_ai", {}).get("negative_prompt", "")

        client = CloudflareAIClient()
        image_data = client.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=self.width,
            height=self.height,
            num_steps=self.num_steps,
            seed=seed,
        )

        output_path.write_bytes(image_data)
        meta_path = output_path.parent / "thumbnail_ai_meta.json"
        meta_data = {
            "video_id": video_id,
            "thumbnail_path": str(output_path),
            "seed": seed,
            "prompt_used": prompt,
        }
        meta_path.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2))
        return output_path

    def _resolve_title(self, metadata: Dict | None, script) -> str:
        if metadata and metadata.get("title"):
            return str(metadata["title"]).strip()
        return script.segments[0].text.strip() if script.segments else "最新ニュース"

    def _build_prompt(self, title: str, description: str, tags: str) -> str:
        from src.utils.config import load_prompts

        prompts = load_prompts()
        ai_config = prompts.get("thumbnail_ai", {})
        template = ai_config.get("template", "")
        fixed_core = ai_config.get("fixed_core", "")

        return template.format(
            fixed_core=fixed_core,
            title=title,
            description=description,
            tags=tags,
        )

    def _generate_seed(self, video_id: str) -> int:
        hash_bytes = hashlib.sha256(video_id.encode()).digest()
        return int.from_bytes(hash_bytes[:8], byteorder="big") & 0x7FFFFFFFFFFFFFFF
