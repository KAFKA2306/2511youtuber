import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.core.io_utils import load_json, write_text
from src.core.step import Step
from src.models import NewsItem, Script, ScriptContextNotes
from src.providers.llm import GeminiProvider, load_prompt_template
from src.tracking import AimTracker
from src.utils.history import load_previous_context
from src.utils.text import extract_code_block


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
        return load_previous_context(run_dir, self.run_id)

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
                    if isinstance(parsed, str):
                        return self._coerce_to_dict(parsed, depth - 1)
                    if isinstance(parsed, dict) and "segments" not in parsed:
                        if mapped := self._dialog_segments_from_mapping(parsed):
                            return {"segments": mapped}
                    return parsed
                except Exception:
                    continue
        stripped = raw.strip()
        if stripped.startswith('"') and stripped.endswith('"'):
            return self._coerce_to_dict(stripped[1:-1], depth - 1)
        if fallback_yaml := self._segments_from_yaml_like(stripped):
            return {"segments": fallback_yaml}
        if fallback := self._dialog_segments_from_text(stripped):
            return {"segments": fallback}
        raise ValueError("Unable to parse script output")

    def _candidates(self, raw: str) -> List[str]:
        text = raw.strip().lstrip("\ufeff")
        candidates = [text]
        if code := extract_code_block(text):
            candidates.append(code)
        if segments := self._extract_segments_block(text):
            candidates.append(segments)
        enriched: List[str] = []
        for c in candidates:
            enriched.extend(self._candidate_variants(c))
        final = []
        seen = set()
        for c in enriched:
            trimmed = c.strip()
            if trimmed and trimmed not in seen:
                seen.add(trimmed)
                final.append(trimmed)
        return final

    def _candidate_variants(self, text: str) -> List[str]:
        variants = [text]
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ("\"", "'"):
            variants.append(text[1:-1])
        normalized = unicodedata.normalize("NFKC", text).replace("　", " ")
        if normalized != text:
            variants.append(normalized)
        quoted = self._quote_text_lines(text)
        if quoted != text:
            variants.append(quoted)
        normalized_quoted = self._quote_text_lines(normalized)
        if normalized_quoted not in variants:
            variants.append(normalized_quoted)
        return variants

    def _quote_text_lines(self, text: str) -> str:
        lines = []
        pattern = re.compile(r"^(\s*text:\s*)(.+?)\s*$")
        for line in text.splitlines():
            match = pattern.match(line)
            if not match:
                lines.append(line)
                continue
            prefix, value = match.groups()
            stripped = value.strip()
            if not stripped or stripped[0] in {'"', "'", '|', '>'}:
                lines.append(line)
                continue
            escaped = stripped.replace('"', '\\"')
            lines.append(f"{prefix}\"{escaped}\"")
        return "\n".join(lines)

    def _extract_segments_block(self, text: str) -> str | None:
        if "segments:" not in text:
            return None
        if match := re.search(r"(?:^|\r?\n)(segments:.*)", text, re.DOTALL):
            return match.group(1)
        return None

    def _segments_from_yaml_like(self, text: str) -> List[Dict[str, str]] | None:
        if "segments" not in text:
            return None
        lines = text.splitlines()
        capture = False
        current: Dict[str, str] | None = None
        results: List[Dict[str, str]] = []
        aliases = self._speaker_aliases()
        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not capture:
                capture = stripped.startswith("segments:")
                continue
            if not stripped:
                continue
            if stripped.startswith("- "):
                if current and "speaker" in current and "text" in current:
                    results.append(current)
                current = {}
                remainder = stripped[1:].strip()
                if remainder.startswith("speaker:"):
                    speaker_value = remainder.split(":", 1)[1].strip()
                    current["speaker"] = aliases.get(speaker_value.replace(" ", ""), speaker_value)
                continue
            if stripped.startswith("speaker:"):
                value = stripped.split(":", 1)[1].strip()
                current = current or {}
                speaker = self._strip_yaml_quotes(value)
                current["speaker"] = aliases.get(speaker.replace(" ", ""), speaker)
                continue
            if stripped.startswith("text:"):
                value = stripped.split(":", 1)[1].strip()
                current = current or {}
                current["text"] = self._decode_yaml_text(value)
                continue
            if current and "text" in current:
                current["text"] += "\n" + stripped
        if current and "speaker" in current and "text" in current:
            results.append(current)
        return results or None

    def _strip_yaml_quotes(self, value: str) -> str:
        cleaned = value.strip()
        if cleaned.startswith(("'", '"')) and cleaned.endswith(("'", '"')) and len(cleaned) >= 2:
            cleaned = cleaned[1:-1]
        return cleaned.replace('\\"', '"').replace("\\'", "'").strip()

    def _decode_yaml_text(self, value: str) -> str:
        stripped = self._strip_yaml_quotes(value)
        return stripped.replace("\\n", "\n").replace('\\"', '"')

    def _dialog_segments_from_text(self, text: str) -> List[Dict[str, str]] | None:
        token = re.compile(r"^(?P<speaker>[^：:]+)[：:](?P<line>.+)$")
        base = self._speaker_aliases()
        segments: List[Dict[str, str]] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = token.match(line)
            if not match:
                if segments:
                    segments[-1]["text"] += "\n" + line
                continue
            speaker_key = match.group("speaker").strip().replace(" ", "")
            speaker = base.get(speaker_key)
            if not speaker:
                continue
            payload = match.group("line").strip()
            if not payload:
                continue
            segments.append({"speaker": speaker, "text": payload})
        return segments or None

    def _dialog_segments_from_mapping(self, data: Dict) -> List[Dict[str, str]] | None:
        base = self._speaker_aliases()
        segments: List[Dict[str, str]] = []
        for key, value in data.items():
            speaker_key = str(key).strip().replace(" ", "")
            speaker = base.get(speaker_key)
            if not speaker:
                continue
            text_value = str(value).strip()
            if not text_value:
                continue
            segments.append({"speaker": speaker, "text": text_value})
        return segments or None

    def _speaker_aliases(self) -> Dict[str, str]:
        aliases: Dict[str, str] = {}
        for value in self.speakers.values():
            primary = str(value).strip()
            cleaned = primary.replace(" ", "")
            aliases[primary] = primary
            aliases[cleaned] = primary
            if cleaned.endswith("さん"):
                aliases[cleaned[:-1]] = primary
            if cleaned.endswith("ちゃん"):
                aliases[cleaned[:-2]] = primary
        narrator = self.speakers.get("narrator")
        if narrator:
            aliases.setdefault("ナレーション", narrator)
            aliases.setdefault("ナレーター", narrator)
        return aliases

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
