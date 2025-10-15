from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict


class StepExecutionError(RuntimeError): ...


class Step(ABC):
    name: str
    output_filename: str
    is_required: bool = True

    def __init__(self, run_id: str, run_dir: Path):
        self.run_id = run_id
        self.run_dir = Path(run_dir)

    @abstractmethod
    def execute(self, inputs: Dict[str, Path]) -> Path: ...

    def get_output_path(self) -> Path:
        return self.run_dir / self.run_id / self.output_filename

    def run(self, inputs: Dict[str, Path]) -> Path:
        output_path = self.get_output_path()
        if output_path.exists():
            return output_path

        output_path = Path(self.execute(inputs))

        if not output_path.exists():
            raise StepExecutionError(f"Step {self.name} did not produce output at {output_path}")

        return output_path
