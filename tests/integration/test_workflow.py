import json
from pathlib import Path

import pytest
from src.workflow import WorkflowOrchestrator
from src.steps.news import NewsCollector
from src.steps.script import ScriptGenerator
from src.steps.audio import AudioSynthesizer
from src.steps.subtitle import SubtitleFormatter
from src.steps.video import VideoRenderer
from src.steps.metadata import MetadataAnalyzer
from src.steps.youtube import YouTubeUploader
from src.steps.base import Step
from src.models import WorkflowState


@pytest.mark.integration
class TestWorkflowIntegration:
    def test_full_workflow_with_dummy_providers(self, temp_run_dir, test_run_id):
        steps = [
            NewsCollector(run_id=test_run_id, run_dir=temp_run_dir, query="テスト", count=2),
            ScriptGenerator(run_id=test_run_id, run_dir=temp_run_dir),
            AudioSynthesizer(run_id=test_run_id, run_dir=temp_run_dir),
            SubtitleFormatter(run_id=test_run_id, run_dir=temp_run_dir),
            VideoRenderer(run_id=test_run_id, run_dir=temp_run_dir),
            MetadataAnalyzer(
                run_id=test_run_id,
                run_dir=temp_run_dir,
                metadata_config={
                    "target_keywords": ["金融", "経済"],
                    "min_keyword_density": 0.01,
                    "max_title_length": 60,
                    "max_description_length": 3500,
                    "default_tags": ["金融ニュース"],
                },
            ),
            YouTubeUploader(
                run_id=test_run_id,
                run_dir=temp_run_dir,
                youtube_config={
                    "dry_run": True,
                    "default_visibility": "unlisted",
                    "category_id": 24,
                    "default_tags": ["金融", "ニュース"],
                },
            ),
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

        if "render_video" in result.outputs:
            assert "analyze_metadata" in result.outputs
            assert (run_path / "metadata.json").exists()
            if "upload_youtube" in result.outputs:
                assert (run_path / "youtube.json").exists()

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

    def test_optional_youtube_failure_keeps_success(self, temp_run_dir, test_run_id):
        class PrecomputedMetadata(Step):
            name = "analyze_metadata"
            output_filename = "metadata.json"

            def execute(self, inputs):
                output_path = self.get_output_path()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump({"title": "test", "description": "desc", "tags": []}, f)
                return output_path

        class FailingUploader(YouTubeUploader):
            def execute(self, inputs):
                raise RuntimeError("upload failed")

        steps = [
            PrecomputedMetadata(run_id=test_run_id, run_dir=temp_run_dir),
            FailingUploader(run_id=test_run_id, run_dir=temp_run_dir),
        ]

        orchestrator = WorkflowOrchestrator(run_id=test_run_id, steps=steps, run_dir=temp_run_dir)
        result = orchestrator.execute()

        assert result.status == "success"
        assert result.errors  # error is recorded but workflow succeeds
