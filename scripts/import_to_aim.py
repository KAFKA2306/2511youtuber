from pathlib import Path

from aim import Run

from src.core.io_utils import load_json


def import_historical_runs(runs_dir: Path = Path("runs")):
    if not runs_dir.exists():
        return

    for run_path in sorted(runs_dir.iterdir()):
        if not run_path.is_dir():
            continue

        run_id = run_path.name
        state_file = run_path / "state.json"
        if not state_file.exists():
            continue

        state = load_json(state_file)
        if not state or state.get("status") != "completed":
            continue

        run = Run(run_hash=run_id, experiment="youtube-ai-v2")

        if "started_at" in state:
            run["started_at"] = state["started_at"]
        if "completed_at" in state:
            run["completed_at"] = state["completed_at"]

        news_data = load_json(run_path / "news.json")
        if news_data:
            run["news_count"] = len(news_data)
            run["news_titles"] = [item.get("title", "") for item in news_data[:3]]

        script_data = load_json(run_path / "script.json")
        if script_data:
            segments = script_data.get("segments", [])
            run["script_segments"] = len(segments)
            run["script_sample"] = "\n".join(
                f"{seg.get('speaker', '')}: {seg.get('text', '')[:50]}" for seg in segments[:3]
            )

        metadata_data = load_json(run_path / "metadata.json")
        if metadata_data:
            run["title"] = metadata_data.get("title", "")
            run["tags"] = metadata_data.get("tags", [])

        run.close()


if __name__ == "__main__":
    import_historical_runs()
