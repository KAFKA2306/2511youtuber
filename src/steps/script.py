import json
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.core.step import Step
from src.models import NewsItem, Script
from src.providers.llm import GeminiProvider, load_prompt_template


class ScriptGenerator(Step):
    name = "generate_script"
    output_filename = "script.json"

    def __init__(self, run_id: str, run_dir: Path, speakers_config: Any | None = None):
        super().__init__(run_id, run_dir)
        if speakers_config is None:
            raise ValueError("Speaker configuration is required")
        data = (
            speakers_config.model_dump()
            if hasattr(speakers_config, "model_dump")
            else dict(speakers_config)
        )
        self.speakers = self._extract_speakers(data)
        self.previous_topics_note, self.previous_next_hint = self._load_previous_context(run_dir)
        self.provider = GeminiProvider()

    def execute(self, inputs: Dict[str, Path]) -> Path:
        news_path = Path(inputs.get("collect_news", ""))
        if not news_path.exists():
            raise ValueError("collect_news input not found")

        news_items = self._load_news(news_path)
        prompt = self._build_prompt(news_items)
        if not self.provider.is_available():
            raise ValueError("Gemini provider is not available")

        raw_output = self.provider.execute(prompt=prompt)
        script = self._parse_and_validate(raw_output)

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(script.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
        return output_path

    def _load_news(self, news_path: Path) -> List[NewsItem]:
        with open(news_path, encoding="utf-8") as f:
            return [NewsItem(**item) for item in json.load(f)]

    def _build_prompt(self, news_items: List[NewsItem]) -> str:
        template = load_prompt_template("script_generation")
        news_text = "\n\n".join(
            f"タイトル: {item.title}\n要約: {item.summary}" for item in news_items
        )
        side_theme = self._pick_side_theme(news_items)
        return template.format(
            news_items=news_text,
            analyst_name=self.speakers["analyst"],
            reporter_name=self.speakers["reporter"],
            narrator_name=self.speakers["narrator"],
            side_theme=side_theme[0],
            side_theme_summary=side_theme[1],
            recent_topics_note=self.previous_topics_note or "直近テーマ情報なし",
            next_theme_note=self.previous_next_hint or "視聴者に次回リクエストをさらっと促す",
        )

    def _load_previous_context(self, run_dir: Path) -> tuple[str, str]:
        base = Path(run_dir)
        if not base.exists():
            return "", ""

        candidates = (
            p for p in sorted(base.iterdir(), reverse=True) if p.is_dir() and p.name != self.run_id
        )
        for candidate in candidates:
            script_path = candidate / "script.json"
            if not script_path.exists():
                continue
            try:
                data = json.loads(script_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            segments = data.get("segments") or []
            if not segments:
                continue

            snippets = [self._summarise_text(seg.get("text", "")) for seg in segments]
            snippets = [s for s in snippets if s]
            if not snippets:
                continue

            recent_summary = " / ".join(snippets[:3])[:220]
            trailing = next((s for s in reversed(snippets) if s), "")[:160]
            return recent_summary, trailing

        return "", ""

    def _summarise_text(self, value: str) -> str:
        text = str(value or "").replace("\n", " ").strip()
        if not text:
            return ""
        if "。" in text:
            text = text.split("。", 1)[0] + "。"
        return text

    def _parse_and_validate(self, raw: str, *, max_depth: int = 6) -> Script:
        data = self._coerce_to_mapping(raw.strip(), max_depth=max_depth)
        if not isinstance(data, dict):
            raise ValueError("Script output must be a mapping")
        return Script(**data)

    def _coerce_to_mapping(self, raw: str, *, max_depth: int) -> Any:
        if max_depth < 0:
            raise ValueError("Maximum recursion depth exceeded during parsing")

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
        if stripped.startswith("\"") and stripped.endswith("\""):
            return self._coerce_to_mapping(stripped[1:-1], max_depth=max_depth - 1)

        raise ValueError("Unable to parse script output")

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

        segments_block = self._extract_segments_block(text)
        if segments_block is not None:
            add(segments_block)

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

    def _extract_segments_block(self, text: str) -> str | None:
        if "segments:" not in text:
            return None
        match = re.search(r"(?:^|\r?\n)(segments:.*)", text, re.DOTALL)
        if match is None:
            return None
        return match.group(1)

    def _pick_side_theme(self, news_items: List[NewsItem]) -> tuple[str, str]:
        for item in news_items:
            title = item.title.strip()
            if title:
                return title, item.summary.strip()
        return ("視聴者投稿リクエスト", "市況の旬ネタを1つ選び、宿題として提示する")

    def _extract_speakers(self, speakers_data: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        required_roles = {"analyst", "reporter", "narrator"}
        extracted: Dict[str, str] = {}
        for role in required_roles:
            info = speakers_data.get(role)
            if not info or not info.get("name"):
                raise ValueError(f"Missing speaker for role {role}")
            extracted[role] = str(info["name"]).strip()
        return extracted
