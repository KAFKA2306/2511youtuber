from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.core.io_utils import load_json, load_script, write_text
from src.core.step import Step
from src.providers.llm import GeminiProvider, load_prompt_template
from src.tracking import AimTracker
from src.utils.logger import get_logger
from src.utils.text import extract_code_block


class MetadataAnalyzer(Step):
    name = "analyze_metadata"
    output_filename = "metadata.json"
    logger = get_logger(__name__)

    def __init__(self, run_id: str, run_dir: Path, metadata_config: Dict | None = None):
        super().__init__(run_id, run_dir)
        cfg = metadata_config or {}
        self.target_keywords = list(cfg.get("target_keywords", []))
        self.max_title_length = int(cfg.get("max_title_length", 50))
        self.max_description_length = int(cfg.get("max_description_length", 5000))
        self.default_tags = list(cfg.get("default_tags", []))
        self.use_llm = bool(cfg.get("use_llm", True))
        tone_cfg = cfg.get("tone") or {}
        self.tone_guidelines = [str(item).strip() for item in tone_cfg.get("guidelines", []) if str(item).strip()]
        self.title_disallowed_terms = [
            str(item).strip() for item in tone_cfg.get("title_disallowed_terms", []) if str(item).strip()
        ]
        self.description_disallowed_terms = [
            str(item).strip() for item in tone_cfg.get("description_disallowed_terms", []) if str(item).strip()
        ]
        replacements_cfg = tone_cfg.get("replacements", {})
        if isinstance(replacements_cfg, dict):
            self.tone_replacements = {str(key): str(value) for key, value in replacements_cfg.items()}
        else:
            self.tone_replacements = {}
        self.llm_provider = (
            GeminiProvider(
                model=cfg.get("llm_model"),
                temperature=cfg.get("llm_temperature"),
                max_tokens=cfg.get("llm_max_tokens"),
            )
            if self.use_llm
            else None
        )

    def execute(self, inputs: Dict[str, Path]) -> Path:
        script_path = inputs.get("generate_script")
        if not script_path or not Path(script_path).exists():
            raise ValueError("Script file not found for metadata analysis")
        script = load_script(Path(script_path))
        news_items = load_json(Path(inputs["collect_news"])) if inputs.get("collect_news") else []

        fallback_title = self._build_title(script)
        fallback_desc = self._build_description(script)
        fallback_tags = self._build_tags(script)
        category_id = 25

        llm_meta = None
        if self.use_llm and self.llm_provider and self.llm_provider.is_available():
            try:
                llm_meta = self._generate_metadata_with_llm(news_items, script)
            except Exception as exc:
                self.logger.warning("LLM metadata generation failed for run %s: %s", self.run_id, exc)

        if llm_meta:
            title = str(llm_meta.get("title", fallback_title))
            description = str(llm_meta.get("description", fallback_desc))
            tags = self._normalize_tags(llm_meta.get("tags")) or fallback_tags
            category_id = int(llm_meta.get("category_id", category_id)) if llm_meta.get("category_id") else category_id
        else:
            title, description, tags = fallback_title, fallback_desc, fallback_tags
        title = self._sanitize_title(title, fallback_title)
        description = self._sanitize_description(description, fallback_desc)

        output = {
            "title": title[: self.max_title_length],
            "description": description[: self.max_description_length],
            "tags": tags[:30],
            "category_id": category_id,
            "analysis": {"segments": len(script.segments), "duration_estimate": script.total_duration_estimate},
        }
        return Path(write_text(self.get_output_path(), json.dumps(output, ensure_ascii=False, indent=2)))

    def _generate_metadata_with_llm(self, news_items: List[Dict], script) -> Dict:
        template = load_prompt_template("metadata_generation")
        news_summary = self._format_news(news_items)
        script_excerpt = "\n".join(f"{seg.speaker}: {seg.text}" for seg in script.segments[:5])
        prompt = template.format(news_items=news_summary, script_excerpt=script_excerpt)
        if self.tone_guidelines:
            prompt = f"{prompt}\n\nトーン調整指針:\n" + "\n".join(f"- {rule}" for rule in self.tone_guidelines)

        tracker = AimTracker.get_instance(self.run_id)
        start = time.time()
        raw_output = self.llm_provider.execute(prompt)
        duration = time.time() - start

        tracker.track_prompt(
            step_name="generate_metadata",
            template_name="metadata_generation",
            prompt=prompt,
            inputs={"news_count": len(news_items), "script_segments": len(script.segments)},
            output=raw_output,
            model=self.llm_provider.model,
            duration=duration,
        )

        return self._parse_response(raw_output)

    def _format_news(self, news_items: List[Dict]) -> str:
        if not news_items:
            return "ニュースデータなし"
        lines = []
        for i, item in enumerate(news_items[:3], 1):
            lines.append(f"{i}. {item.get('title', '無題')}\n   {item.get('summary', '')[:200]}")
        return "\n\n".join(lines)

    def _parse_response(self, response: str) -> Dict:
        data = self._coerce_to_dict(response)
        if not isinstance(data, dict):
            raise ValueError("Metadata YAML must be a mapping")
        return data

    def _coerce_to_dict(self, raw: str, depth: int = 6) -> Any:
        if depth < 0:
            raise ValueError("Maximum recursion depth exceeded during metadata parsing")
        for candidate in self._candidates(raw):
            for loader in (yaml.safe_load, json.loads):
                try:
                    parsed = loader(candidate)
                    return self._coerce_to_dict(parsed, depth - 1) if isinstance(parsed, str) else parsed
                except Exception:
                    continue
        stripped = raw.strip()
        if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
            return self._coerce_to_dict(stripped[1:-1], depth - 1)
        raise ValueError("Unable to parse metadata output")

    def _candidates(self, raw: str) -> List[str]:
        text = raw.strip().lstrip("\ufeff")
        candidates = [text]
        if code := extract_code_block(text):
            candidates.append(code)
        if triple := self._extract_triple_quote(text):
            candidates.append(triple)
        if yaml_body := self._extract_yaml_body(text):
            candidates.append(yaml_body)
        for c in list(candidates):
            if len(c) >= 2 and c[0] == c[-1] and c[0] in {'"', "'"}:
                candidates.append(c[1:-1])
        return list(dict.fromkeys(c.strip() for c in candidates if c.strip()))

    def _extract_triple_quote(self, text: str) -> str | None:
        if match := re.search(r"'''\s*\n?(.*?)\n?'''", text, re.DOTALL):
            return match.group(1)
        if match := re.search(r'"""\s*\n?(.*?)\n?"""', text, re.DOTALL):
            return match.group(1)
        return None

    def _extract_yaml_body(self, text: str) -> str | None:
        if match := re.search(r"(?:^|\r?\n)(title:\s.*)", text, re.DOTALL):
            return match.group(1)
        return None

    def _build_title(self, script) -> str:
        base = script.segments[0].text if script.segments else "金融ニュース速報"
        if len(base) > self.max_title_length:
            base = base[: self.max_title_length - 1] + "…"
        if not base.endswith("ニュース") and not base.endswith("速報"):
            base = f"{base}｜金融ニュース"
        return base[: self.max_title_length]

    def _build_description(self, script) -> str:
        lines = ["本動画では以下のトピックを扱います:"]
        for seg in script.segments:
            lines.append(f"{seg.speaker}：{seg.text}")
        desc = "\n".join(lines)
        return desc[: self.max_description_length - 1] + "…" if len(desc) > self.max_description_length else desc

    def _build_tags(self, script) -> List[str]:
        tags = list(self.default_tags)
        full_text = "".join(seg.text for seg in script.segments)
        for keyword in ["金融", "経済", "ニュース", "投資", "株価", "市場", "速報"]:
            if keyword in full_text:
                tags.append(keyword)
        return list(dict.fromkeys(tags))[:30]

    def _normalize_tags(self, tags: Any) -> List[str]:
        if isinstance(tags, list):
            if cleaned := [str(tag).strip() for tag in tags if str(tag).strip()]:
                return cleaned[:30]
        if isinstance(tags, str) and tags.strip():
            return [part.strip() for part in tags.split(",") if part.strip()][:30]
        return []

    def _sanitize_title(self, value: str, fallback: str) -> str:
        sanitized = self._apply_replacements(value)
        sanitized = self._remove_terms(sanitized, self.title_disallowed_terms)
        sanitized = sanitized.strip()
        if not sanitized:
            sanitized = fallback
        sanitized = self._apply_replacements(sanitized)
        sanitized = self._remove_terms(sanitized, self.title_disallowed_terms)
        return sanitized if sanitized else fallback

    def _sanitize_description(self, value: str, fallback: str) -> str:
        sanitized = self._apply_replacements(value)
        sanitized = self._remove_terms(sanitized, self.description_disallowed_terms)
        return sanitized if sanitized.strip() else fallback

    def _apply_replacements(self, text: str) -> str:
        result = text
        for source, target in self.tone_replacements.items():
            result = result.replace(source, target)
        return result

    def _remove_terms(self, text: str, terms: List[str]) -> str:
        result = text
        for term in terms:
            if term in result and term not in self.tone_replacements:
                result = result.replace(term, "")
        return result
