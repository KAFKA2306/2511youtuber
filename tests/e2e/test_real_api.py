import pytest
import os
from pathlib import Path
from src.providers.llm import GeminiProvider
from src.steps.news import NewsCollector
from src.steps.script import ScriptGenerator
from src.workflow import WorkflowOrchestrator


@pytest.mark.e2e
class TestRealGeminiAPI:
    def test_gemini_api_availability(self):
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        provider = GeminiProvider()
        assert provider.is_available()

    def test_gemini_script_generation(self):
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        provider = GeminiProvider()

        prompt = """
以下のニュースから対話形式のスクリプトを生成してください。

ニュース:
タイトル: テストニュース
要約: これはテストです。

出力形式（YAML）:
```yaml
segments:
  - speaker: 田中
    text: こんにちは
  - speaker: 鈴木
    text: よろしくお願いします
```
"""

        response = provider.execute(prompt=prompt)

        assert response is not None
        assert len(response) > 50
        assert "segments" in response or "田中" in response

    def test_full_workflow_with_real_gemini(self, temp_run_dir, test_run_id):
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        steps = [
            NewsCollector(run_id=test_run_id, run_dir=temp_run_dir, count=2),
            ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir)
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
