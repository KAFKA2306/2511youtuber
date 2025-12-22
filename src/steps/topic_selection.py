import json
import time
from pathlib import Path
from typing import Dict

from src.core.step import Step
from src.providers.llm import GeminiProvider
from src.tracking import AimTracker
from src.utils.history import gather_recent_topics
from src.utils.config import load_prompts


class TopicSelector(Step):
    name = "select_topic"
    output_filename = "topic_selection.json"

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        provider: GeminiProvider,
        recent_topics_runs: int = 30,
        recent_topics_max_chars: int = 2000,
    ):
        super().__init__(run_id, run_dir)
        self.provider = provider
        self.recent_topics_runs = recent_topics_runs
        self.recent_topics_max_chars = recent_topics_max_chars
        self.prompts = load_prompts()["topic_selection"]

    def execute(self, inputs: Dict[str, Path]) -> Path:
        recent_topics = gather_recent_topics(self.run_dir, self.run_id, self.recent_topics_runs)
        recent_note = " / ".join(recent_topics) if recent_topics else "直近テーマ情報なし"
        if self.recent_topics_max_chars > 0:
            recent_note = recent_note[: self.recent_topics_max_chars]

        tracker = AimTracker.get_instance(self.run_id)
        
        user_prompt = self.prompts["user_template"].format(recent_topics_note=recent_note)
        system_prompt = self.prompts["system"]
        prompt_data = {"recent_topics_note": recent_note}
        prompt_log = json.dumps(prompt_data, ensure_ascii=False)

        start = time.time()
        
        try:
            response_content = self.provider.execute(prompt=user_prompt, system_prompt=system_prompt)
            # Remove markdown code fences if present
            cleaned = response_content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            selection = json.loads(cleaned)
        except Exception as e:
            # Fallback to a default query if selection fails
            print(f"Topic selection failed: {e}. Using default query.")
            selection = {"query": "", "topic": "Default Topic", "category": "Fallback"}

        duration = time.time() - start

        tracker.track_prompt(
            step_name="select_topic",
            template_name="topic_selection",
            prompt=prompt_log,
            inputs=prompt_data,
            output=json.dumps(selection, ensure_ascii=False),
            model=self.provider.model,
            duration=duration,
        )

        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(selection, f, ensure_ascii=False, indent=2)
            
        return output_path
