from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

import yaml

from src.models import Script
from src.providers.llm import GeminiProvider, load_prompt_template
from src.steps.base import Step


class MetadataAnalyzer(Step):
    name = "analyze_metadata"
    output_filename = "metadata.json"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        metadata_config: Dict | None = None,
    ) -> None:
        super().__init__(run_id, run_dir)
        metadata_config = metadata_config or {}
        self.target_keywords: List[str] = list(metadata_config.get("target_keywords", []))
        self.max_title_length: int = int(metadata_config.get("max_title_length", 50))
        self.max_description_length: int = int(metadata_config.get("max_description_length", 5000))
        self.default_tags: List[str] = list(metadata_config.get("default_tags", []))
        self.use_llm: bool = bool(metadata_config.get("use_llm", True))
        self.llm_provider: GeminiProvider | None = None

        if self.use_llm:
            model = metadata_config.get("llm_model", "gemini/gemini-2.5-flash-preview-09-2025")
            self.llm_provider = GeminiProvider(model=model, temperature=0.7)

    def execute(self, inputs: Dict[str, Path]) -> Path:
        script_path = inputs.get("generate_script")
        news_path = inputs.get("collect_news")

        if not script_path or not Path(script_path).exists():
            raise ValueError("Script file not found for metadata analysis")

        script = self._load_script(Path(script_path))

        news_items = []
        if news_path and Path(news_path).exists():
            news_items = self._load_news(Path(news_path))

        if self.use_llm and self.llm_provider and self.llm_provider.is_available():
            llm_metadata = self._generate_metadata_with_llm(news_items, script)
            title = llm_metadata.get("title", "")
            description = llm_metadata.get("description", "")
            tags = llm_metadata.get("tags", [])
            category_id = llm_metadata.get("category_id", 25)
        else:
            title = self._build_title(script)
            description = self._build_description(script)
            tags = self._build_tags_from_script(script)
            category_id = 25

        recommendations: List[str] = []

        output = {
            "title": title[: self.max_title_length],
            "description": description[: self.max_description_length],
            "tags": tags[:30],
            "category_id": category_id,
            "analysis": {
                "segments": len(script.segments),
                "duration_estimate": script.total_duration_estimate,
            },
            "recommendations": recommendations,
        }

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        return output_path

    def _load_script(self, path: Path) -> Script:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)

    def _load_news(self, path: Path) -> List[Dict]:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _generate_metadata_with_llm(self, news_items: List[Dict], script: Script) -> Dict:
        prompt_template = load_prompt_template("metadata_generation")

        news_summary = self._format_news_for_prompt(news_items)
        script_excerpt = self._format_script_for_prompt(script)

        prompt = prompt_template.format(news_items=news_summary, script_excerpt=script_excerpt)

        response = self.llm_provider.execute(prompt)
        metadata = self._parse_llm_response(response)

        return metadata

    def _format_news_for_prompt(self, news_items: List[Dict]) -> str:
        if not news_items:
            return "ニュースデータなし"

        lines = []
        for i, item in enumerate(news_items[:3], 1):
            title = item.get("title", "無題")
            summary = item.get("summary", "")[:200]
            lines.append(f"{i}. {title}\n   {summary}")

        return "\n\n".join(lines)

    def _format_script_for_prompt(self, script: Script) -> str:
        excerpts = []
        for segment in script.segments[:5]:
            excerpts.append(f"{segment.speaker}: {segment.text}")

        return "\n".join(excerpts)

    def _parse_llm_response(self, response: str) -> Dict:
        match = re.search(r"```(?:yaml|yml)\n(.*?)```", response, re.DOTALL)
        yaml_str = match.group(1) if match else response

        metadata = yaml.safe_load(yaml_str)
        if not isinstance(metadata, dict):
            raise ValueError("Metadata YAML must be a mapping")
        return metadata

    def _build_title(self, script: Script) -> str:
        base = script.segments[0].text if script.segments else "金融ニュース速報"
        if len(base) > self.max_title_length:
            base = base[: self.max_title_length - 1] + "…"
        if not base.endswith("ニュース") and not base.endswith("速報"):
            base = f"{base}｜金融ニュース"
        return base[: self.max_title_length]

    def _build_description(self, script: Script) -> str:
        lines = ["本動画では以下のトピックを扱います:"]
        for segment in script.segments:
            lines.append(f"{segment.speaker}：{segment.text}")
        description = "\n".join(lines)
        if len(description) > self.max_description_length:
            description = description[: self.max_description_length - 1] + "…"
        return description

    def _build_tags_from_script(self, script: Script) -> List[str]:
        tags = list(self.default_tags)
        full_text = "".join(segment.text for segment in script.segments)

        keywords = ["金融", "経済", "ニュース", "投資", "株価", "市場", "速報"]
        for keyword in keywords:
            if keyword in full_text:
                tags.append(keyword)

        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                unique_tags.append(tag)
                seen.add(tag)
        return unique_tags[:30]
