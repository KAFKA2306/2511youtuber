from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Dict

from PIL import Image, ImageDraw, ImageOps

from src.core.io_utils import load_json
from src.core.step import Step
from src.providers.cloudflare_ai import CloudflareAIClient
from src.providers.llm import GeminiProvider
from src.steps.thumbnail import ThumbnailGenerator
from src.utils.config import Config, load_prompts


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
        self.text_overlay_enabled = bool(cfg.get("text_overlay_enabled", True))

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
                    "text_overlay": "deterministic-local" if self.text_overlay_enabled else "disabled",
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
        if self.text_overlay_enabled:
            image_data = self._compose_title(image_data, title)
        output_path.write_bytes(image_data)
        return output_path

    def _resolve_title(self, metadata: Dict) -> str:
        return str(metadata["title"]).strip()

    def _compose_title(self, image_data: bytes, title: str) -> bytes:
        """Render exact title text locally over an AI-generated background.

        The image model is intentionally responsible only for the visual background.
        Text is rendered with the repository's normal thumbnail typography so the
        requested Japanese copy is deterministic and auditable.
        """
        with Image.open(BytesIO(image_data)) as source:
            image = ImageOps.fit(
                source.convert("RGBA"),
                (self.width, self.height),
                method=Image.Resampling.LANCZOS,
            )

        text_cfg = Config.load().steps.thumbnail.model_dump()
        text_cfg.update(
            {
                "enabled": True,
                "width": self.width,
                "height": self.height,
                "randomize_palette": False,
                "show_subtitle": False,
                "overlays": [],
            }
        )
        renderer = ThumbnailGenerator(self.run_id, self.run_dir, text_cfg)
        draw = ImageDraw.Draw(image)
        margin_x, margin_y = renderer._safe_margins()
        text_right = self.width - margin_x - max(0, renderer.right_guard_band_px)
        max_title_height = int(self.height * renderer.title_height_max_pct / 100)
        title_font, _ = renderer._fit_title_font(title, text_right - margin_x, max_title_height)
        renderer._render_text(
            draw,
            title,
            title_font,
            renderer.title_color,
            margin_y,
            text_right,
            left_edge=margin_x,
        )

        result = BytesIO()
        image.convert("RGB").save(result, format="PNG")
        return result.getvalue()

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
