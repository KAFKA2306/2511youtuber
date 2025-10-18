from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from src.core.state import WorkflowResult, WorkflowState
from src.core.step import Step
from src.tracking import AimTracker


class WorkflowOrchestrator:
    def __init__(self, run_id: str, steps: Iterable[Step], run_dir: Path):
        self.run_id = run_id
        self.steps: List[Step] = list(steps)
        self.run_dir = Path(run_dir)
        self.state = WorkflowState.load_or_create(run_id, self.run_dir)

    def execute(self) -> WorkflowResult:
        start_time = datetime.now()
        tracker = AimTracker.get_instance(self.run_id)

        for step in self.steps:
            if step.name in self.state.completed_steps:
                continue

            output_path = step.run(self.state.outputs)
            self.state.mark_completed(step.name, str(output_path))
            self.state.save(self.run_dir)

        self.state.mark_success()
        self.state.save(self.run_dir)
        duration = (datetime.now() - start_time).total_seconds()

        prev_outputs = self._load_previous_outputs()
        if prev_outputs:
            tracker.track_diff(self.run_id, prev_outputs, self.state.outputs)

        tracker.track_metrics({"workflow_duration": duration, "steps_count": len(self.state.completed_steps)})
        tracker.finalize()

        return WorkflowResult(
            status="success",
            run_id=self.run_id,
            outputs=self.state.outputs,
            errors=self.state.errors,
            duration_seconds=duration,
        )

    def _load_previous_outputs(self) -> Dict[str, Path]:
        if not self.run_dir.exists():
            return {}
        candidates = sorted(
            [p for p in self.run_dir.iterdir() if p.is_dir() and p.name != self.run_id], reverse=True
        )
        for candidate in candidates:
            state_path = candidate / "state.json"
            if state_path.exists():
                prev_state = WorkflowState.load_or_create("", candidate.parent)
                if prev_state.status == "completed":
                    return {k: Path(v) for k, v in prev_state.outputs.items()}
        return {}
