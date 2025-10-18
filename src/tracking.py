from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any, Dict, List

from aim import Run


class AimTracker:
    _instance = None
    _run = None

    @classmethod
    def get_instance(cls, run_id: str | None = None) -> "AimTracker":
        if cls._instance is None:
            cls._instance = cls(run_id)
        return cls._instance

    def __init__(self, run_id: str | None = None):
        self._run = Run(run_hash=run_id, experiment="youtube-ai-v2")

    def track_prompt(
        self,
        step_name: str,
        template_name: str,
        inputs: Dict[str, Any],
        output: str,
        model: str = "",
        duration: float = 0.0,
    ):
        self._run.track(
            {
                "template": template_name,
                "model": model,
                "duration": duration,
                "input_tokens": sum(len(str(v)) for v in inputs.values()),
                "output_tokens": len(output),
            },
            name=f"{step_name}_prompt",
            context={"template": template_name},
        )
        self._run[f"{step_name}_inputs"] = inputs
        self._run[f"{step_name}_output"] = output[:10000]

    def track_diff(self, run_id: str, prev_outputs: Dict[str, Path], curr_outputs: Dict[str, Path]):
        diffs = {}
        for key in {"generate_script", "generate_metadata"}:
            prev_path = prev_outputs.get(key)
            curr_path = curr_outputs.get(key)
            if not prev_path or not curr_path:
                continue
            prev_path = Path(prev_path)
            curr_path = Path(curr_path)
            if not prev_path.exists() or not curr_path.exists():
                continue

            prev_content = self._load_content(prev_path)
            curr_content = self._load_content(curr_path)
            if prev_content and curr_content:
                diff = self._compute_diff(prev_content, curr_content)
                diffs[key] = diff
                self._run.track(
                    {
                        "added_lines": diff["added"],
                        "removed_lines": diff["removed"],
                        "similarity": diff["similarity"],
                    },
                    name=f"{key}_diff",
                )

        self._run["diffs"] = diffs

    def track_metrics(self, metrics: Dict[str, float]):
        for name, value in metrics.items():
            self._run.track(value, name=name)

    def finalize(self):
        if self._run:
            self._run.close()

    def _load_content(self, path: Path) -> List[str]:
        if not path.exists():
            return []
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(content)
            if isinstance(data, dict):
                if "segments" in data:
                    return [seg.get("text", "") for seg in data["segments"] if isinstance(seg, dict)]
                if "title" in data and "description" in data:
                    return [data.get("title", ""), data.get("description", "")]
        return content.splitlines()

    def _compute_diff(self, prev: List[str], curr: List[str]) -> Dict[str, Any]:
        matcher = difflib.SequenceMatcher(None, prev, curr)
        ratio = matcher.ratio()

        added = sum(1 for tag, _, _, _, _ in matcher.get_opcodes() if tag == "insert")
        removed = sum(1 for tag, _, _, _, _ in matcher.get_opcodes() if tag == "delete")

        return {"added": added, "removed": removed, "similarity": ratio}
