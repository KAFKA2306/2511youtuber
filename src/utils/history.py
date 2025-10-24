from __future__ import annotations

from pathlib import Path
from typing import Iterator, List

from src.core.io_utils import load_json
from src.models import ScriptContextNotes


def iter_previous_runs(run_dir: Path, current_run_id: str) -> Iterator[Path]:
    base = Path(run_dir)
    if not base.exists():
        return
    for candidate in sorted(base.iterdir(), reverse=True):
        if candidate.is_dir() and candidate.name != current_run_id:
            yield candidate


def extract_script_notes(run_path: Path) -> ScriptContextNotes:
    script_data = load_json(run_path / "script.json")
    notes = ScriptContextNotes.from_mapping(script_data)
    if notes.recent_topics_note or notes.next_theme_note:
        return notes
    for name in ("metadata.json", "youtube.json"):
        data = load_json(run_path / name)
        title = extract_title(data)
        if title:
            return ScriptContextNotes(recent_topics_note=title)
    return ScriptContextNotes()


def extract_title(data: dict) -> str:
    title = str(data.get("title") or "").strip()
    if title:
        return title
    nested = data.get("metadata")
    if isinstance(nested, dict):
        nested_title = str(nested.get("title") or "").strip()
        if nested_title:
            return nested_title
    return ""


def load_previous_context(run_dir: Path, current_run_id: str) -> ScriptContextNotes:
    for candidate in iter_previous_runs(run_dir, current_run_id):
        notes = extract_script_notes(candidate)
        if not notes.is_empty():
            return notes
    return ScriptContextNotes()


def gather_recent_topics(run_dir: Path, current_run_id: str, limit: int) -> List[str]:
    topics: List[str] = []
    if limit <= 0:
        return topics
    for candidate in iter_previous_runs(run_dir, current_run_id):
        note = extract_script_notes(candidate).recent_topics_note
        if note:
            topics.append(note)
        if len(topics) >= limit:
            break
    return topics
