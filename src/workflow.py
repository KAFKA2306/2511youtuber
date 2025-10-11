from datetime import datetime
from pathlib import Path
from typing import List

from src.models import WorkflowResult, WorkflowState
from src.steps.base import CriticalError, Step
from src.utils.logger import get_logger


class WorkflowOrchestrator:
    def __init__(self, run_id: str, steps: List[Step], run_dir: Path):
        self.run_id = run_id
        self.steps = steps
        self.run_dir = Path(run_dir)
        self.state = WorkflowState.load_or_create(run_id, self.run_dir)
        self.logger = get_logger(self.__class__.__name__)

    def execute(self) -> WorkflowResult:
        start_time = datetime.now()
        self.logger.info("Starting workflow", run_id=self.run_id, steps_count=len(self.steps))

        for step in self.steps:
            if step.name in self.state.completed_steps:
                self.logger.info("Skipping completed step", step=step.name)
                continue

            try:
                output_path = step.run(self.state.outputs)
                self.state.mark_completed(step.name, str(output_path))
                self.state.save(self.run_dir)

            except CriticalError as e:
                self.logger.critical("Critical error in step", step=step.name, error=str(e))
                self.state.mark_failed(str(e))
                self.state.save(self.run_dir)

                return WorkflowResult(
                    status="failed",
                    run_id=self.run_id,
                    outputs=self.state.outputs,
                    errors=self.state.errors,
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                )

            except Exception as e:
                self.logger.error("Error in step", step=step.name, error=str(e))
                self.state.errors.append(f"{step.name}: {str(e)}")

                if step.is_required:
                    self.logger.warning("Required step failed, marking workflow as partial")
                    self.state.status = "partial"
                    self.state.save(self.run_dir)

                    return WorkflowResult(
                        status="partial",
                        run_id=self.run_id,
                        outputs=self.state.outputs,
                        errors=self.state.errors,
                        duration_seconds=(datetime.now() - start_time).total_seconds(),
                    )

        self.state.mark_success()
        self.state.save(self.run_dir)

        duration = (datetime.now() - start_time).total_seconds()
        self.logger.info("Workflow completed successfully", run_id=self.run_id, duration_seconds=duration)

        return WorkflowResult(
            status="success",
            run_id=self.run_id,
            outputs=self.state.outputs,
            errors=self.state.errors,
            duration_seconds=duration,
        )
