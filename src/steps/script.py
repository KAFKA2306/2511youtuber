import json
import re
import textwrap
import yaml
from pathlib import Path
from typing import Dict
from src.steps.base import Step
from src.providers.base import ProviderChain
from src.providers.llm import GeminiProvider, DummyLLMProvider, load_prompt_template
from src.models import Script, NewsItem
from src.utils.logger import get_logger


logger = get_logger(__name__)


class ScriptGenerator(Step):
    name = "generate_script"
    output_filename = "script.json"

    def execute(self, inputs: Dict[str, Path]) -> Path:
        news_path = inputs.get("collect_news")
        if not news_path or not Path(news_path).exists():
            raise ValueError("News file not found")

        news_items = self._load_news(Path(news_path))
        self.logger.info(f"Loaded news items", count=len(news_items))

        llm_chain = ProviderChain([
            GeminiProvider(),
            DummyLLMProvider()
        ])

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
            purity=script.japanese_purity(),
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

        return template.format(news_items=news_text)

    def _parse_and_validate(self, raw: str, max_depth: int = 3) -> Script:
        raw = textwrap.dedent(raw).strip()

        for attempt in range(max_depth):
            raw = self._strip_wrappers(raw)
            raw = textwrap.dedent(raw).strip()

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
                script = Script(**data)

                purity = script.japanese_purity()
                if purity < 1.0:
                    self.logger.warning(f"Japanese purity below 1.0: {purity}")

                return script

            if isinstance(data, str):
                self.logger.info(f"Recursively unwrapping string", attempt=attempt)
                raw = data
                continue

            if data is not None:
                raise ValueError(f"Unexpected data type: {type(data)}")

        raise ValueError("Max recursion depth exceeded while parsing LLM output")

    def _strip_wrappers(self, raw: str) -> str:
        cleaned = raw.strip()

        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned[3:-3]
            cleaned = cleaned.lstrip()

            first_line, separator, remainder = cleaned.partition("\n")
            if separator:
                candidate = first_line.strip()
                if candidate and re.fullmatch(r"[a-zA-Z0-9_+\-.]+", candidate):
                    cleaned = remainder.lstrip("\n")
                else:
                    cleaned = first_line + separator + remainder

            cleaned = cleaned.strip()

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
