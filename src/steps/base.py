from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict

from src.utils.logger import get_logger


class Step(ABC):
    name: str
    output_filename: str
    is_required: bool = True

    def __init__(self, run_id: str, run_dir: Path):
        self.run_id = run_id
        self.run_dir = run_dir
        self.logger = get_logger(f"Step.{self.name}")

    @abstractmethod
    def execute(self, inputs: Dict[str, Path]) -> Path:
        pass

    def get_output_path(self) -> Path:
        return self.run_dir / self.run_id / self.output_filename

    def output_exists(self) -> bool:
        return self.get_output_path().exists()

    def run(self, inputs: Dict[str, Path]) -> Path:
        if self.output_exists():
            self.logger.info(f"Step {self.name} already completed, skipping")
            return self.get_output_path()

        self.logger.info(f"Executing step {self.name}")
        output_path = self.execute(inputs)

        if not output_path.exists():
            raise StepExecutionError(f"Step {self.name} did not produce output at {output_path}")

        self.logger.info(f"Step {self.name} completed", output_path=str(output_path))
        return output_path


class StepExecutionError(Exception):
    pass


class CriticalError(Exception):
    pass
