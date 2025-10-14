from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from src.core.state import WorkflowResult, WorkflowState
from src.core.step import Step


class WorkflowOrchestrator:
    def __init__(self, run_id: str, steps: Iterable[Step], run_dir: Path):
        self.run_id = run_id
        self.steps: List[Step] = list(steps)
        self.run_dir = Path(run_dir)
        self.state = WorkflowState.load_or_create(run_id, self.run_dir)

    def execute(self) -> WorkflowResult:
        start_time = datetime.now()
        for step in self.steps:
            if step.name in self.state.completed_steps:
                continue

            output_path = step.run(self.state.outputs)
            self.state.mark_completed(step.name, str(output_path))
            self.state.save(self.run_dir)
        self.state.mark_success()
        self.state.save(self.run_dir)
        duration = (datetime.now() - start_time).total_seconds()
        return WorkflowResult(
            status="success",
            run_id=self.run_id,
            outputs=self.state.outputs,
            errors=self.state.errors,
            duration_seconds=duration,
        )
