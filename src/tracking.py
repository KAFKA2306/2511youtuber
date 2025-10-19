from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any, Dict, List

from aim import Run


def _repo_path() -> Path:
    base = Path(__file__).resolve().parents[1] / ".aim"
    base.mkdir(parents=True, exist_ok=True)
    return base


def load_lines(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            segments = data.get("segments")
            if isinstance(segments, list):
                lines: List[str] = []
                for item in segments:
                    if isinstance(item, dict):
                        value = item.get("text", "")
                    else:
                        value = getattr(item, "text", "")
                    if value:
                        lines.append(str(value))
                if lines:
                    return lines
            title = data.get("title")
            description = data.get("description")
            if isinstance(title, str) and isinstance(description, str):
                return [title, description]
    return text.splitlines()


def diff_stats(prev: List[str], curr: List[str]) -> Dict[str, float]:
    matcher = difflib.SequenceMatcher(None, prev, curr)
    added = sum(1 for tag, _, _, _, _ in matcher.get_opcodes() if tag == "insert")
    removed = sum(1 for tag, _, _, _, _ in matcher.get_opcodes() if tag == "delete")
    return {"added": added, "removed": removed, "similarity": matcher.ratio()}


class AimTracker:
    _instance: "AimTracker" | None = None
    _active_run_id: str | None = None

    @classmethod
    def get_instance(cls, run_id: str | None = None) -> "AimTracker":
        if cls._instance is None or (run_id and cls._active_run_id != run_id):
            cls._instance = cls(run_id)
            cls._active_run_id = cls._instance.run_id
        return cls._instance

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or ""
        self._run = Run(repo=_repo_path(), experiment="youtube-ai-v2")
        if self.run_id:
            self._run["run_id"] = self.run_id

    def track_prompt(
        self,
        step_name: str,
        template_name: str,
        prompt: str,
        inputs: Dict[str, Any],
        output: str,
        model: str = "",
        duration: float = 0.0,
    ) -> None:
        payload: Dict[str, Any] = {
            "duration": duration,
            "prompt_length": len(prompt),
            "output_length": len(output),
        }
        if template_name:
            payload["template"] = template_name
        if model:
            payload["model"] = model
        for key, value in inputs.items():
            if isinstance(value, (int, float)):
                payload[f"input_{key}"] = value
        self._run.track(payload, name=f"{step_name}_prompt")
        self._run[f"{step_name}_template"] = template_name
        self._run[f"{step_name}_prompt"] = prompt[:10000]
        self._run[f"{step_name}_inputs"] = {str(k): self._serialize(v) for k, v in inputs.items()}
        self._run[f"{step_name}_output"] = output[:10000]

    def track_diff(self, prev_outputs: Dict[str, Path | str], curr_outputs: Dict[str, Path | str]) -> None:
        pairs = [
            ("generate_script", prev_outputs.get("generate_script"), curr_outputs.get("generate_script")),
            (
                "generate_metadata",
                prev_outputs.get("generate_metadata") or prev_outputs.get("analyze_metadata"),
                curr_outputs.get("generate_metadata") or curr_outputs.get("analyze_metadata"),
            ),
        ]
        for label, prev_value, curr_value in pairs:
            if not prev_value or not curr_value:
                continue
            prev_path = Path(prev_value)
            curr_path = Path(curr_value)
            if not prev_path.exists() or not curr_path.exists():
                continue
            prev_lines = load_lines(prev_path)
            curr_lines = load_lines(curr_path)
            if not prev_lines and not curr_lines:
                continue
            diff = diff_stats(prev_lines, curr_lines)
            for metric, value in diff.items():
                self._run.track(value, name=f"{label}_diff_{metric}")
            self._run[f"{label}_diff"] = diff

    def track_metrics(self, metrics: Dict[str, float]) -> None:
        for name, value in metrics.items():
            self._run.track(value, name=name)

    def finalize(self) -> None:
        if self._run:
            self._run.close()
            self._run = None
        AimTracker._instance = None
        AimTracker._active_run_id = None

    def _serialize(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return [self._serialize(v) for v in value]
        if isinstance(value, dict):
            return {str(k): self._serialize(v) for k, v in value.items()}
        return str(value)
