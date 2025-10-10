from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List

from src.models import Script
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
        self.min_keyword_density: float = float(metadata_config.get("min_keyword_density", 0.01))
        self.max_title_length: int = int(metadata_config.get("max_title_length", 60))
        self.max_description_length: int = int(metadata_config.get("max_description_length", 3500))
        self.default_tags: List[str] = list(metadata_config.get("default_tags", []))

    def execute(self, inputs: Dict[str, Path]) -> Path:
        script_path = inputs.get("generate_script")
        if not script_path or not Path(script_path).exists():
            raise ValueError("Script file not found for metadata analysis")

        script = self._load_script(Path(script_path))
        full_text = "".join(segment.text for segment in script.segments)

        keyword_report = self._analyze_keywords(full_text)
        recommendations = self._build_recommendations(keyword_report)

        title = self._build_title(script)
        description = self._build_description(script)
        tags = self._build_tags(keyword_report)

        output = {
            "title": title,
            "description": description,
            "tags": tags,
            "analysis": {
                "segments": len(script.segments),
                "duration_estimate": script.total_duration_estimate,
                "keyword_density": keyword_report,
            },
            "recommendations": recommendations,
        }

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        self.logger.info(
            "Metadata analysis completed",
            tags=len(tags),
            recommendations=len(recommendations),
        )

        return output_path

    def _load_script(self, path: Path) -> Script:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)

    def _analyze_keywords(self, text: str) -> Dict[str, Dict[str, float]]:
        if not text:
            return {kw: {"count": 0, "density": 0.0} for kw in self.target_keywords}

        counts = Counter()
        for keyword in self.target_keywords:
            counts[keyword] = text.count(keyword)

        total_length = max(len(text), 1)
        return {
            keyword: {
                "count": counts[keyword],
                "density": counts[keyword] / total_length,
            }
            for keyword in self.target_keywords
        }

    def _build_recommendations(self, keyword_report: Dict[str, Dict[str, float]]) -> List[str]:
        recommendations: List[str] = []
        for keyword, data in keyword_report.items():
            if data["density"] < self.min_keyword_density:
                recommendations.append(
                    f"キーワード『{keyword}』の含有率が低いため、原稿で強調してください。"
                )
        if not recommendations:
            recommendations.append("主要キーワードの密度は目標値を満たしています。")
        return recommendations

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

    def _build_tags(self, keyword_report: Dict[str, Dict[str, float]]) -> List[str]:
        tags = list(self.default_tags)
        for keyword, data in keyword_report.items():
            if data["count"] > 0:
                tags.append(keyword)

        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                unique_tags.append(tag)
                seen.add(tag)
        return unique_tags[:30]

