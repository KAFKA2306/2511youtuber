from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.orchestrator import WorkflowOrchestrator
from src.core.step import Step, StepExecutionError


class DummyStep(Step):
    def __init__(self, run_id: str, run_dir: Path, name: str, output_filename: str, marker: str) -> None:
        self.name = name
        self.output_filename = output_filename
        super().__init__(run_id, run_dir)
        self.marker = marker
        self.executions = 0

    def execute(self, inputs: dict[str, Path]) -> Path:
        self.executions += 1
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.marker, encoding="utf-8")
        return output_path


class MissingOutputStep(Step):
    name = "missing"
    output_filename = "missing.txt"

    def execute(self, inputs: dict[str, Path]) -> Path:
        return self.get_output_path()


def test_workflow_orchestrator_persists_state(tmp_path: Path) -> None:
    run_id = "run-123"
    step_a = DummyStep(run_id, tmp_path, "step_a", "a.txt", "A")
    step_b = DummyStep(run_id, tmp_path, "step_b", "b.txt", "B")

    orchestrator = WorkflowOrchestrator(run_id, [step_a, step_b], tmp_path)
    result = orchestrator.execute()

    assert result.status == "success"
    assert result.outputs == {"step_a": str(step_a.get_output_path()), "step_b": str(step_b.get_output_path())}
    assert step_a.executions == 1
    assert step_b.executions == 1

    state_path = tmp_path / run_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["completed_steps"] == ["step_a", "step_b"]
    assert data["status"] == "completed"

    new_step_a = DummyStep(run_id, tmp_path, "step_a", "a.txt", "A2")
    new_step_b = DummyStep(run_id, tmp_path, "step_b", "b.txt", "B2")

    second_run = WorkflowOrchestrator(run_id, [new_step_a, new_step_b], tmp_path).execute()

    assert second_run.outputs == result.outputs
    assert new_step_a.executions == 0
    assert new_step_b.executions == 0


def test_step_run_raises_when_output_missing(tmp_path: Path) -> None:
    step = MissingOutputStep("run", tmp_path)

    with pytest.raises(StepExecutionError) as excinfo:
        step.run({})

    assert "missing" in str(excinfo.value)
