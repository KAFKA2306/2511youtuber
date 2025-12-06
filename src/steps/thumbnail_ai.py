from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from src.core.io_utils import load_json
from src.core.step import Step
from src.providers.cloudflare_ai import CloudflareAIClient
from src.providers.llm import GeminiProvider
from src.utils.config import load_prompts


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
        metadata = load_json(Path(inputs["analyze_metadata"])) if inputs.get("analyze_metadata") else None
        title = self._resolve_title(metadata)
        description, tags = (
            (str(metadata.get("description", "")).strip(), ", ".join(metadata.get("tags", [])))
            if metadata
            else ("", "")
        )
        prompts = load_prompts()
        prompt_en = self._generate_prompt(prompts, title, description, tags)
        negative_prompt = prompts.get("thumbnail_ai", {}).get("negative_prompt", "")
        (output_path.parent / "thumbnail_ai_prompt.json").write_text(
            json.dumps(
                {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "prompt": prompt_en,
                    "negative_prompt": negative_prompt,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        image_data = CloudflareAIClient().generate_image(
            prompt=prompt_en,
            negative_prompt=negative_prompt,
            width=self.width,
            height=self.height,
            num_steps=self.num_steps,
        )
        output_path.write_bytes(image_data)
        return output_path

    def _resolve_title(self, metadata: Dict) -> str:
        return str(metadata["title"]).strip()

    def _generate_prompt(self, prompts: Dict, title: str, description: str, tags: str) -> str:
        ai_config = prompts.get("thumbnail_ai", {})
        fixed_core = ai_config.get("fixed_core", "")
        composition = ai_config.get("composition_guidelines", "")
        quality = ai_config.get("quality_modifiers", "")
        trans = prompts.get("thumbnail_translation", {})
        return (
            GeminiProvider()
            .execute(
                prompt=trans.get("user_template", "").format(
                    fixed_core=fixed_core,
                    title=title,
                    description=description,
                    tags=tags,
                    quality_modifiers=quality,
                    composition_guidelines=composition,
                ),
                system_prompt=trans.get("system", ""),
            )
            .strip()
        )
