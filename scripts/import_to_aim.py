from __future__ import annotations

import json
from pathlib import Path

from aim import Run

from src.tracking import diff_stats, load_lines


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    runs_dir = root / "runs"
    if not runs_dir.exists():
        return
    previous: dict[str, list[str]] = {}
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        run_id = run_dir.name
        run = Run(run_hash=run_id, experiment="youtube-ai-v2")
        state_path = run_dir / "state.json"
        if state_path.exists():
            run["state"] = json.loads(state_path.read_text(encoding="utf-8"))
        for step, filename in (
            ("collect_news", "news.json"),
            ("generate_script", "script.json"),
            ("generate_metadata", "metadata.json"),
        ):
            path = run_dir / filename
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            run[f"{step}_output"] = content[:10000]
            if step in {"generate_script", "generate_metadata"}:
                current_lines = load_lines(path)
                previous_lines = previous.get(step)
                if previous_lines:
                    diff = diff_stats(previous_lines, current_lines)
                    run.track(diff, name=f"{step}_diff")
                    run[f"{step}_diff"] = diff
                previous[step] = current_lines
        run.close()


if __name__ == "__main__":
    main()
