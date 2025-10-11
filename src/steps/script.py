import json
import textwrap
import yaml
import re
from pathlib import Path
from typing import Dict, Any
from src.steps.base import Step
from src.providers.base import ProviderChain
from src.providers.llm import GeminiProvider, DummyLLMProvider, load_prompt_template
from src.models import Script, NewsItem
from src.utils.logger import get_logger


logger = get_logger(__name__)


class ScriptGenerator(Step):
    name = "generate_script"
    output_filename = "script.json"

    def __init__(self, run_id: str, run_dir: Path, speakers_config: Any | None = None):
        super().__init__(run_id, run_dir)
        self.speaker_profiles = self._prepare_speaker_profiles(speakers_config)
        self.alias_map = self._build_alias_map(self.speaker_profiles)
        self.canonical_roles = {role: profile["name"] for role, profile in self.speaker_profiles.items()}
        narrator = self.canonical_roles.get("narrator")
        fallback = next((name for name in self.canonical_roles.values() if name), "")
        self.default_speaker = narrator or fallback

    def execute(self, inputs: Dict[str, Path]) -> Path:
        news_path = inputs.get("collect_news")
        if not news_path or not Path(news_path).exists():
            raise ValueError("News file not found")

        news_items = self._load_news(Path(news_path))
        self.logger.info(f"Loaded news items", count=len(news_items))

        llm_chain = self._build_llm_chain()

        prompt = self._build_prompt(news_items)
        raw_output = llm_chain.execute(prompt=prompt)

        script = self._parse_and_validate(raw_output)

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(script.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

        self.logger.info(
            f"Script generated",
            segments=len(script.segments),
            output_path=str(output_path)
        )
        return output_path

    def _load_news(self, news_path: Path) -> list[NewsItem]:
        with open(news_path, encoding="utf-8") as f:
            data = json.load(f)
        return [NewsItem(**item) for item in data]

    def _build_prompt(self, news_items: list[NewsItem]) -> str:
        template = load_prompt_template("script_generation")

        news_text = "\n\n".join([
            f"タイトル: {item.title}\n要約: {item.summary}"
            for item in news_items
        ])
        return template.format(
            news_items=news_text,
            analyst_name=self.canonical_roles.get("analyst", ""),
            reporter_name=self.canonical_roles.get("reporter", ""),
            narrator_name=self.canonical_roles.get("narrator", "")
        )

    def _parse_and_validate(self, raw: str, max_depth: int = 3) -> Script:
        raw = textwrap.dedent(raw).strip()

        for attempt in range(max_depth):
            raw = self._strip_wrappers(raw)
            raw = textwrap.dedent(raw).strip()
            raw = self._sanitize_parenthetical_annotations(raw)

            data = None
            try:
                data = yaml.safe_load(raw)
            except yaml.YAMLError as e:
                self.logger.warning(f"YAML parse failed, trying JSON", error=str(e))

            if data is None:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = None

            if isinstance(data, dict):
                data = self._normalise_segments_data(data)
                script = Script(**data)
                return script

            if isinstance(data, str):
                self.logger.info(f"Recursively unwrapping string", attempt=attempt)
                raw = data
                continue

            if data is None:
                extracted = self._extract_segment_block(raw)
                if extracted and extracted != raw:
                    self.logger.info("Extracted YAML segment block from LLM output", attempt=attempt)
                    raw = extracted
                    continue

            if data is not None:
                raise ValueError(f"Unexpected data type: {type(data)}")

        raise ValueError("Max recursion depth exceeded while parsing LLM output")

    def _strip_wrappers(self, raw: str) -> str:
        cleaned = raw.strip()

        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned[3:-3]

        wrappers = [
            ('"""', '"""'),
            ("'''", "'''"),
            ('"', '"'),
            ("'", "'")
        ]

        for prefix, suffix in wrappers:
            if cleaned.startswith(prefix) and cleaned.endswith(suffix) and len(cleaned) >= len(prefix) + len(suffix):
                cleaned = cleaned[len(prefix):-len(suffix)]
                cleaned = cleaned.strip()
                break

        return cleaned

    def _extract_segment_block(self, raw: str) -> str | None:
        marker = "segments:"
        if marker not in raw:
            return None

        start = raw.index(marker)
        candidate = raw[start:]
        candidate = candidate.strip()

        if "```" in candidate:
            candidate = candidate.split("```", 1)[0].strip()

        return candidate if candidate else None

    def _normalise_segments_data(self, data: dict) -> dict:
        segments = data.get("segments")
        if not isinstance(segments, list):
            return data

        for segment in segments:
            if not isinstance(segment, dict):
                continue
            text = segment.get("text")
            if isinstance(text, str):
                segment["text"] = self._to_full_width(text)
            speaker = segment.get("speaker")
            if isinstance(speaker, str):
                segment["speaker"] = self._normalise_speaker(speaker)

        return data

    def _to_full_width(self, text: str) -> str:
        converted = []
        for char in text:
            if "!" <= char <= "~":
                converted.append(chr(ord(char) + 0xFEE0))
            else:
                converted.append(char)
        return "".join(converted)

    def _normalise_speaker(self, value: str) -> str:
        cleaned = value.strip()
        if cleaned in self.alias_map:
            return self.alias_map[cleaned]
        for alias, canonical in self.alias_map.items():
            if alias and alias in cleaned:
                return canonical
        return self.default_speaker

    def _sanitize_parenthetical_annotations(self, raw: str) -> str:
        pattern = re.compile(r'（([^）]*?):')

        def _replace(match: re.Match[str]) -> str:
            inner = match.group(1)
            return f'（{inner}：'

        return pattern.sub(_replace, raw)

    def _prepare_speaker_profiles(self, config: Any | None) -> Dict[str, Dict[str, Any]]:
        if config is None:
            raise ValueError("Speaker configuration is required")
        if hasattr(config, "model_dump"):
            config = config.model_dump()
        profiles = {
            role: {
                "name": info.get("name", "").strip(),
                "aliases": [alias.strip() for alias in info.get("aliases", []) if alias]
            }
            for role, info in dict(config).items()
        }
        for role, profile in profiles.items():
            if not profile["name"]:
                raise ValueError(f"Speaker name missing for role: {role}")
        return profiles

    def _build_alias_map(self, profiles: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for profile in profiles.values():
            canonical = profile.get("name", "").strip()
            if canonical:
                mapping[canonical] = canonical
            for alias in profile.get("aliases", []):
                mapping[alias] = canonical
        return mapping

    def _build_llm_chain(self) -> ProviderChain:
        speakers = [
            self.canonical_roles.get("analyst", ""),
            self.canonical_roles.get("reporter", ""),
            self.canonical_roles.get("narrator", "")
        ]
        speakers = [name for name in speakers if name]
        return ProviderChain([
            GeminiProvider(),
            DummyLLMProvider(speakers=speakers)
        ])
