from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal

from pydantic import BaseModel, Field


class WorkflowState(BaseModel):
    run_id: str
    status: Literal["running", "completed", "failed", "partial"] = "running"
    completed_steps: List[str] = Field(default_factory=list)
    outputs: Dict[str, str] = Field(default_factory=dict)
    step_statuses: Dict[str, Literal["pending", "success", "failed"]] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @classmethod
    def load_or_create(cls, run_id: str, run_dir: Path) -> "WorkflowState":
        state_path = run_dir / run_id / "state.json"
        if state_path.exists():
            data = json.loads(state_path.read_text(encoding="utf-8"))
            return cls(**data)
        return cls(run_id=run_id)

    def save(self, run_dir: Path):
        state_path = run_dir / self.run_id / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, indent=2)
        state_path.write_text(payload, encoding="utf-8")

    def mark_completed(self, step_name: str, output_path: str):
        if step_name not in self.completed_steps:
            self.completed_steps.append(step_name)
        self.outputs[step_name] = output_path
        self.step_statuses[step_name] = "success"

    def mark_failed(self, step_name: str, error: str):
        self.status = "failed"
        if step_name:
            self.step_statuses[step_name] = "failed"
        self.errors.append(error)
        self.completed_at = datetime.now()

    def mark_success(self):
        self.status = "completed"
        self.completed_at = datetime.now()


class WorkflowResult(BaseModel):
    status: Literal["success", "failed", "partial"]
    run_id: str
    outputs: Dict[str, str]
    errors: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
