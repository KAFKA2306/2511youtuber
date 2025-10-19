from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from aim import Run

from src.tracking import diff_stats, load_lines


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    runs_dir = root / "runs"
    if not runs_dir.exists():
        return
    previous: dict[str, list[str]] = {}
    repo = root / ".aim"
    repo.mkdir(parents=True, exist_ok=True)
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        run_id = run_dir.name
        run = Run(repo=repo, experiment="youtube-ai-v2")
        run["run_id"] = run_id
        state_path = run_dir / "state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            run["state"] = state
            start = state.get("started_at")
            end = state.get("completed_at")
            if start and end:
                duration = (
                    datetime.fromisoformat(end) - datetime.fromisoformat(start)
                ).total_seconds()
                run.track(duration, name="workflow_duration")
            steps = state.get("completed_steps")
            if isinstance(steps, list):
                run.track(len(steps), name="steps_count")
        targets = {
            "output_news": "news.json",
            "output_script": "script.json",
            "output_metadata": "metadata.json",
            "output_youtube": "youtube.json",
            "output_tweet": "tweet.json",
            "output_query": "query.json",
        }
        payloads: dict[str, object] = {}
        for key, filename in targets.items():
            path = run_dir / filename
            if not path.exists():
                continue
            payloads[key] = json.loads(path.read_text(encoding="utf-8"))
        for key, data in payloads.items():
            run[key] = data
        for step, key in (("generate_script", "output_script"), ("generate_metadata", "output_metadata")):
            data = payloads.get(key)
            path = run_dir / targets[key]
            if not data or not path.exists():
                continue
            current_lines = load_lines(path)
            previous_lines = previous.get(step)
            if previous_lines:
                diff = diff_stats(previous_lines, current_lines)
                for metric, value in diff.items():
                    run.track(value, name=f"{step}_diff_{metric}")
                run[f"{step}_diff"] = diff
            previous[step] = current_lines
        news = payloads.get("output_news")
        if isinstance(news, list):
            run.track(len(news), name="news_count")
        run.close()


if __name__ == "__main__":
    main()
