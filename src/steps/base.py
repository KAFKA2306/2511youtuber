from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict


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

    def output_exists(self) -> bool:
        return self.get_output_path().exists()

    def run(self, inputs: Dict[str, Path]) -> Path:
        if self.output_exists():
            return self.get_output_path()

        output_path = self.execute(inputs)

        if not output_path.exists():
            raise FileNotFoundError(f"Step {self.name} did not produce output at {output_path}")

        return output_path
