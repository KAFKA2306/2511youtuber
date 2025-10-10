import pytest
from pathlib import Path
import json
from src.workflow import WorkflowOrchestrator
from src.steps.news import NewsCollector
from src.steps.script import ScriptGenerator
from src.steps.audio import AudioSynthesizer
from src.steps.subtitle import SubtitleFormatter
from src.steps.video import VideoRenderer
from src.models import WorkflowState


@pytest.mark.integration
class TestWorkflowIntegration:
    def test_full_workflow_with_dummy_providers(self, temp_run_dir, test_run_id):
        steps = [
            NewsCollector(run_id=test_run_id, run_dir=temp_run_dir, query="テスト", count=2),
            ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir),
            AudioSynthesizer(run_id=test_run_id, run_dir=temp_run_dir),
            SubtitleFormatter(run_id=test_run_id, run_dir=temp_run_dir),
            VideoRenderer(run_id=test_run_id, run_dir=temp_run_dir)
        ]

        orchestrator = WorkflowOrchestrator(run_id=test_run_id, steps=steps, run_dir=temp_run_dir)
        result = orchestrator.execute()

        assert result.status in ["success", "partial"]
        assert len(result.outputs) >= 2
        assert "collect_news" in result.outputs
        assert "generate_script" in result.outputs

        run_path = temp_run_dir / test_run_id
        assert run_path.exists()
        assert (run_path / "news.json").exists()
        assert (run_path / "script.json").exists()
        assert (run_path / "state.json").exists()

    def test_checkpoint_resume(self, temp_run_dir, test_run_id):
        steps = [
            NewsCollector(run_id=test_run_id, run_dir=temp_run_dir, query="テスト", count=2),
            ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir)
        ]

        orchestrator1 = WorkflowOrchestrator(run_id=test_run_id, steps=steps, run_dir=temp_run_dir)
        result1 = orchestrator1.execute()

        assert "collect_news" in result1.outputs
        assert "generate_script" in result1.outputs

        orchestrator2 = WorkflowOrchestrator(run_id=test_run_id, steps=steps, run_dir=temp_run_dir)
        result2 = orchestrator2.execute()

        assert result2.status in ["success", "partial"]
        assert len(result2.outputs) == len(result1.outputs)

    def test_workflow_state_persistence(self, temp_run_dir, test_run_id):
        state = WorkflowState(run_id=test_run_id)
        state.mark_completed("test_step", "/path/to/output")
        state.save(temp_run_dir)

        loaded_state = WorkflowState.load_or_create(test_run_id, temp_run_dir)

        assert loaded_state.run_id == test_run_id
        assert "test_step" in loaded_state.completed_steps
        assert loaded_state.outputs["test_step"] == "/path/to/output"

    def test_partial_workflow_failure(self, temp_run_dir, test_run_id):
        class FailingStep(NewsCollector):
            def execute(self, inputs):
                raise Exception("Intentional failure")

        steps = [
            FailingStep(run_id=test_run_id, run_dir=temp_run_dir)
        ]

        orchestrator = WorkflowOrchestrator(run_id=test_run_id, steps=steps, run_dir=temp_run_dir)
        result = orchestrator.execute()

        assert result.status in ["failed", "partial"]
        assert len(result.errors) > 0
