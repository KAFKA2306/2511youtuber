import json
from pathlib import Path
from typing import Any, Dict, List

from src.models import NewsItem, Script
from src.providers.llm import GeminiProvider, load_prompt_template
from src.steps.base import Step


class ScriptGenerator(Step):
    name = "generate_script"
    output_filename = "script.json"

    def __init__(self, run_id: str, run_dir: Path, speakers_config: Any | None = None):
        super().__init__(run_id, run_dir)
        if speakers_config is None:
            raise ValueError("Speaker configuration is required")
        if hasattr(speakers_config, "model_dump"):
            speakers_data = speakers_config.model_dump()
        else:
            speakers_data = dict(speakers_config)
        self.speakers = self._extract_speakers(speakers_data)
        self.provider = GeminiProvider()

    def execute(self, inputs: Dict[str, Path]) -> Path:
        news_path = Path(inputs["collect_news"])
        news_items = self._load_news(news_path)
        prompt = self._build_prompt(news_items)
        if not self.provider.is_available():
            raise ValueError("Gemini provider is not available")
        raw_output = self.provider.execute(prompt=prompt)
        script = self._parse_output(raw_output)
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(script.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
        return output_path

    def _load_news(self, news_path: Path) -> List[NewsItem]:
        with open(news_path, encoding="utf-8") as f:
            data = json.load(f)
        return [NewsItem(**item) for item in data]

    def _build_prompt(self, news_items: List[NewsItem]) -> str:
        template = load_prompt_template("script_generation")
        news_text = "\n\n".join([f"タイトル: {item.title}\n要約: {item.summary}" for item in news_items])
        return template.format(
            news_items=news_text,
            analyst_name=self.speakers["analyst"],
            reporter_name=self.speakers["reporter"],
            narrator_name=self.speakers["narrator"],
        )

    def _parse_output(self, raw: str) -> Script:
        cleaned = raw.strip()
        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("\n", 1)[0]
        data = json.loads(cleaned)
        return Script(**data)

    def _extract_speakers(self, speakers_data: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        required_roles = {"analyst", "reporter", "narrator"}
        extracted: Dict[str, str] = {}
        for role in required_roles:
            info = speakers_data.get(role)
            if not info or not info.get("name"):
                raise ValueError(f"Missing speaker for role {role}")
            extracted[role] = str(info["name"]).strip()
        return extracted
