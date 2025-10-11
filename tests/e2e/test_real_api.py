import pytest
from pathlib import Path
from src.providers.llm import GeminiProvider
from src.steps.news import NewsCollector
from src.steps.script import ScriptGenerator
from src.utils.config import Config
from src.utils.secrets import load_secret_values
from src.workflow import WorkflowOrchestrator


@pytest.mark.e2e
class TestRealGeminiAPI:
    @staticmethod
    def _has_real_gemini_key() -> bool:
        return bool(load_secret_values("GEMINI_API_KEY"))

    def test_gemini_api_availability(self):
        if not self._has_real_gemini_key():
            pytest.skip("GEMINI_API_KEY not set")

        provider = GeminiProvider()
        assert provider.is_available()

    def test_gemini_script_generation(self):
        if not self._has_real_gemini_key():
            pytest.skip("GEMINI_API_KEY not set")

        provider = GeminiProvider()

        speakers = Config.load().steps.script.speakers
        analyst = speakers.analyst.name
        reporter = speakers.reporter.name
        narrator = speakers.narrator.name

        prompt = f"""
以下のニュースから対話形式のスクリプトを生成してください。

ニュース:
タイトル: テストニュース
要約: これはテストです。

出力形式（YAML）:
```yaml
segments:
  - speaker: {analyst}
    text: こんにちは
  - speaker: {reporter}
    text: よろしくお願いします
  - speaker: {narrator}
    text: それでは始めましょう
```
"""

        response = provider.execute(prompt=prompt)

        assert response is not None
        assert len(response) > 50
        assert "segments" in response or analyst in response

    def test_full_workflow_with_real_gemini(self, temp_run_dir, test_run_id):
        if not self._has_real_gemini_key():
            pytest.skip("GEMINI_API_KEY not set")

        speakers = Config.load().steps.script.speakers

        steps = [
            NewsCollector(run_id=test_run_id, run_dir=temp_run_dir, count=2),
            ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir, speakers_config=speakers)
        ]

        orchestrator = WorkflowOrchestrator(run_id=test_run_id, steps=steps, run_dir=temp_run_dir)
        result = orchestrator.execute()

        assert result.status in ["success", "partial"]
        assert "collect_news" in result.outputs
        assert "generate_script" in result.outputs

        script_path = Path(result.outputs["generate_script"])
        assert script_path.exists()

        import json
        with open(script_path, encoding="utf-8") as f:
            data = json.load(f)

        from src.models import Script
        script = Script(**data)
        assert len(script.segments) >= 3
