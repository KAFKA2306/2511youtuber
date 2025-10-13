from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.core.step import Step
from src.models import Script
from src.providers.llm import GeminiProvider, load_prompt_template


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
            self.llm_provider = GeminiProvider(
                model=metadata_config.get("llm_model"),
                temperature=metadata_config.get("llm_temperature"),
                max_tokens=metadata_config.get("llm_max_tokens"),
            )

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

        output = {
            "title": title[: self.max_title_length],
            "description": description[: self.max_description_length],
            "tags": tags[:30],
            "category_id": category_id,
            "analysis": {
                "segments": len(script.segments),
                "duration_estimate": script.total_duration_estimate,
            },
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
        data = self._coerce_to_mapping(response)
        if not isinstance(data, dict):
            raise ValueError("Metadata YAML must be a mapping")
        return data

    def _coerce_to_mapping(self, raw: str, *, max_depth: int = 6) -> Any:
        if max_depth < 0:
            raise ValueError("Maximum recursion depth exceeded during metadata parsing")

        for candidate in self._candidate_payloads(raw):
            for loader in (yaml.safe_load, json.loads):
                try:
                    parsed = loader(candidate)
                except Exception:
                    continue
                if isinstance(parsed, str):
                    return self._coerce_to_mapping(parsed, max_depth=max_depth - 1)
                return parsed

        stripped = raw.strip()
        if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
            return self._coerce_to_mapping(stripped[1:-1], max_depth=max_depth - 1)

        raise ValueError("Unable to parse metadata output")

    def _candidate_payloads(self, raw: str) -> List[str]:
        text = raw.strip().lstrip("\ufeff")
        candidates: List[str] = []

        def add(value: str) -> None:
            value = value.strip()
            if value and value not in candidates:
                candidates.append(value)

        add(text)

        code_block = self._extract_code_block(text)
        if code_block is not None:
            add(code_block)

        triple_block = self._extract_triple_quote_block(text)
        if triple_block is not None:
            add(triple_block)

        yaml_body = self._extract_yaml_body(text)
        if yaml_body is not None:
            add(yaml_body)

        original_candidates = list(candidates)
        for value in original_candidates:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                add(value[1:-1])

        return candidates

    def _extract_code_block(self, text: str) -> str | None:
        if "```" not in text:
            return None
        match = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)```", text, re.DOTALL)
        if match is None:
            return None
        return match.group(1)

    def _extract_triple_quote_block(self, text: str) -> str | None:
        match = re.search(r"'''\s*\n?(.*?)\n?'''", text, re.DOTALL)
        if match:
            return match.group(1)
        match = re.search(r'"""\s*\n?(.*?)\n?"""', text, re.DOTALL)
        if match:
            return match.group(1)
        return None

    def _extract_yaml_body(self, text: str) -> str | None:
        match = re.search(r"(?:^|\r?\n)(title:\s.*)", text, re.DOTALL)
        if match is None:
            return None
        return match.group(1)

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
