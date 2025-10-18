import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping

import yaml

from src.core.io_utils import load_json, write_text
from src.core.step import Step
from src.models import NewsItem, Script
from src.providers.llm import GeminiProvider, load_prompt_template
from src.tracking import AimTracker


@dataclass
class ScriptContextNotes:
    recent_topics_note: str = ""
    next_theme_note: str = ""

    def to_mapping(self) -> Dict[str, str]:
        return {"recent_topics_note": self.recent_topics_note, "next_theme_note": self.next_theme_note}

    def merge_missing(self, other: "ScriptContextNotes") -> "ScriptContextNotes":
        if not other:
            return self
        return ScriptContextNotes(
            recent_topics_note=self.recent_topics_note or other.recent_topics_note,
            next_theme_note=self.next_theme_note or other.next_theme_note,
        )

    def is_empty(self) -> bool:
        return not (self.recent_topics_note or self.next_theme_note)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> "ScriptContextNotes":
        if not data:
            return cls()
        recent = str(data.get("recent_topics_note") or data.get("recent_topic_note") or "").strip()
        next_note = str(data.get("next_theme_note") or "").strip()
        return cls(recent_topics_note=recent, next_theme_note=next_note)


class ScriptGenerator(Step):
    name = "generate_script"
    output_filename = "script.json"

    def __init__(self, run_id: str, run_dir: Path, speakers_config: Any | None = None):
        super().__init__(run_id, run_dir)
        if not speakers_config:
            raise ValueError("Speaker configuration is required")
        data = speakers_config.model_dump() if hasattr(speakers_config, "model_dump") else dict(speakers_config)
        self.speakers = self._extract_speakers(data)
        self.carryover_notes = self._load_previous_context(run_dir)
        self.provider = GeminiProvider()

    def execute(self, inputs: Dict[str, Path]) -> Path:
        news_path = Path(inputs.get("collect_news", ""))
        if not news_path.exists():
            raise ValueError("collect_news input not found")
        news_items = [NewsItem(**item) for item in load_json(news_path)]
        if not self.provider.is_available():
            raise ValueError("Gemini provider is not available")

        prompt = self._build_prompt(news_items)
        tracker = AimTracker.get_instance(self.run_id)

        start = time.time()
        raw_output = self.provider.execute(prompt=prompt)
        duration = time.time() - start

        tracker.track_prompt(
            step_name="generate_script",
            template_name="script_generation",
            prompt=prompt,
            inputs={"news_count": len(news_items), "recent_topics": self.carryover_notes.recent_topics_note[:200]},
            output=raw_output,
            model=self.provider.model,
            duration=duration,
        )

        script = self._parse_and_validate(raw_output)
        generated_notes = self._context_from_segments(script.segments)
        script = script.model_copy(update=generated_notes.to_mapping())
        self.carryover_notes = generated_notes
        return Path(
            write_text(self.get_output_path(), json.dumps(script.model_dump(mode="json"), ensure_ascii=False, indent=2))
        )

    def _build_prompt(self, news_items: List[NewsItem]) -> str:
        template = load_prompt_template("script_generation")
        news_text = "\n\n".join(f"タイトル: {item.title}\n要約: {item.summary}" for item in news_items)
        side_theme = self._pick_side_theme(news_items)
        return template.format(
            news_items=news_text,
            analyst_name=self.speakers["analyst"],
            reporter_name=self.speakers["reporter"],
            narrator_name=self.speakers["narrator"],
            side_theme=side_theme[0],
            side_theme_summary=side_theme[1],
            recent_topics_note=self.carryover_notes.recent_topics_note or "直近テーマ情報なし",
            next_theme_note="今日のテーマから派生する新しい視点や発見の余地",
        )

    def _load_previous_context(self, run_dir: Path) -> ScriptContextNotes:
        base = Path(run_dir)
        if not base.exists():
            return ScriptContextNotes()
        candidates = [p for p in sorted(base.iterdir(), reverse=True) if p.is_dir() and p.name != self.run_id]
        for candidate in candidates:
            notes = ScriptContextNotes()
            if script_data := load_json(candidate / "script.json"):
                notes = ScriptContextNotes.from_mapping(script_data)
                if notes.is_empty() and (segments := script_data.get("segments")):
                    notes = notes.merge_missing(self._context_from_segments(segments))
            if not notes.recent_topics_note:
                if metadata_title := self._extract_title(candidate / "metadata.json"):
                    notes = notes.merge_missing(ScriptContextNotes(recent_topics_note=metadata_title))
            if not notes.recent_topics_note:
                if youtube_title := self._extract_title(candidate / "youtube.json"):
                    notes = notes.merge_missing(ScriptContextNotes(recent_topics_note=youtube_title))
            if not notes.is_empty():
                return notes
        return ScriptContextNotes()

    def _context_from_segments(self, segments: List[Any]) -> ScriptContextNotes:
        snippets = []
        for seg in segments:
            if hasattr(seg, "text"):
                text = seg.text
            elif isinstance(seg, dict):
                text = seg.get("text", "")
            else:
                text = ""
            if snippet := self._summarise(text):
                snippets.append(snippet)
        if not snippets:
            return ScriptContextNotes()
        recent_summary = " / ".join(snippets[:3])[:220]
        trailing = next((s for s in reversed(snippets) if s), "")[:160]
        return ScriptContextNotes(recent_topics_note=recent_summary, next_theme_note=trailing)

    def _summarise(self, value: str) -> str:
        text = str(value or "").replace("\n", " ").strip()
        if not text:
            return ""
        return text.split("。", 1)[0] + "。" if "。" in text else text

    def _extract_title(self, path: Path) -> str:
        if not (data := load_json(path)):
            return ""
        if title := str(data.get("title") or "").strip():
            return title
        if nested := data.get("metadata"):
            if isinstance(nested, dict) and (nested_title := str(nested.get("title") or "").strip()):
                return nested_title
        return ""

    def _parse_and_validate(self, raw: str, depth: int = 6) -> Script:
        data = self._coerce_to_dict(raw.strip(), depth)
        if not isinstance(data, dict):
            raise ValueError("Script output must be a mapping")
        script = Script(**data)
        for seg in script.segments:
            seg.text = re.sub(r'。(?![\r\n]|$)', '。\n', seg.text)
        return script

    def _coerce_to_dict(self, raw: str, depth: int) -> Any:
        if depth < 0:
            raise ValueError("Maximum recursion depth exceeded during parsing")
        for candidate in self._candidates(raw):
            for loader in (yaml.safe_load, json.loads):
                try:
                    parsed = loader(candidate)
                    return self._coerce_to_dict(parsed, depth - 1) if isinstance(parsed, str) else parsed
                except Exception:
                    continue
        stripped = raw.strip()
        if stripped.startswith('"') and stripped.endswith('"'):
            return self._coerce_to_dict(stripped[1:-1], depth - 1)
        raise ValueError("Unable to parse script output")

    def _candidates(self, raw: str) -> List[str]:
        text = raw.strip().lstrip("\ufeff")
        candidates = [text]
        if code := self._extract_code_block(text):
            candidates.append(code)
        if segments := self._extract_segments_block(text):
            candidates.append(segments)
        for c in list(candidates):
            if len(c) >= 2 and c[0] == c[-1] and c[0] in {'"', "'"}:
                candidates.append(c[1:-1])
        return list(dict.fromkeys(c.strip() for c in candidates if c.strip()))

    def _extract_code_block(self, text: str) -> str | None:
        if "```" not in text:
            return None
        if match := re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)```", text, re.DOTALL):
            return match.group(1)
        return None

    def _extract_segments_block(self, text: str) -> str | None:
        if "segments:" not in text:
            return None
        if match := re.search(r"(?:^|\r?\n)(segments:.*)", text, re.DOTALL):
            return match.group(1)
        return None

    def _pick_side_theme(self, news_items: List[NewsItem]) -> tuple[str, str]:
        for item in news_items:
            if title := item.title.strip():
                return title, item.summary.strip()
        return ("視聴者投稿リクエスト", "市況の旬ネタを1つ選び、宿題として提示する")

    def _extract_speakers(self, speakers_data: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        extracted = {}
        for role in {"analyst", "reporter", "narrator"}:
            info = speakers_data.get(role)
            if not info or not info.get("name"):
                raise ValueError(f"Missing speaker for role {role}")
            extracted[role] = str(info["name"]).strip()
        return extracted
