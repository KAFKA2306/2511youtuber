import shutil

import pytest

from src.models import WorkflowState
from src.steps.script import ScriptGenerator
from src.utils.config import Config
from src.workflow import WorkflowOrchestrator


@pytest.mark.integration
class TestWorkflowIntegration:
    def test_checkpoint_resume(self, temp_run_dir, test_run_id, sample_news_path):
        run_path = temp_run_dir / test_run_id
        run_path.mkdir(parents=True, exist_ok=True)
        news_output = run_path / "news.json"
        shutil.copy(sample_news_path, news_output)

        state = WorkflowState(run_id=test_run_id)
        state.mark_completed("collect_news", str(news_output))
        state.save(temp_run_dir)

        speakers_config = Config.load().steps.script.speakers
        steps = [ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir, speakers_config=speakers_config)]

        orchestrator1 = WorkflowOrchestrator(run_id=test_run_id, steps=steps, run_dir=temp_run_dir)
        result1 = orchestrator1.execute()

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
