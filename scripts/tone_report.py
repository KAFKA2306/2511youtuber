from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--aim-db", default=".aim/run_metadata.sqlite")
    parser.add_argument("--output", default=None)
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args()


def load_metadata(runs_dir: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if not runs_dir.exists():
        return entries
    for path in sorted(runs_dir.iterdir()):
        if not path.is_dir():
            continue
        data_path = path / "metadata.json"
        if not data_path.exists():
            continue
        data = json.loads(data_path.read_text(encoding="utf-8"))
        title = str(data.get("title", "") or "")
        description = str(data.get("description", "") or "")
        entries.append(
            {
                "run_id": path.name,
                "title": title,
                "description": description,
                "title_length": len(title),
                "description_length": len(description),
            }
        )
    return entries


def detect_terms(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    flagged_terms = [
        "闇",
        "陰謀",
        "暴露",
        "暴落",
        "崩壊",
        "激震",
        "ショック",
        "警告",
        "危機",
        "炎上",
        "やばい",
        "震撼",
        "衝撃",
        "暴走",
        "緊急速報",
    ]
    title_counter: Counter[str] = Counter()
    description_counter: Counter[str] = Counter()
    title_examples: List[Dict[str, Any]] = []
    description_examples: List[Dict[str, Any]] = []
    for entry in entries:
        title_hits = sorted({term for term in flagged_terms if term in entry["title"]})
        desc_hits = sorted({term for term in flagged_terms if term in entry["description"]})
        if title_hits:
            for term in title_hits:
                title_counter[term] += 1
            title_examples.append(
                {
                    "run_id": entry["run_id"],
                    "terms": title_hits,
                    "title": entry["title"],
                }
            )
        if desc_hits:
            for term in desc_hits:
                description_counter[term] += 1
            description_examples.append(
                {
                    "run_id": entry["run_id"],
                    "terms": desc_hits,
                    "excerpt": entry["description"][:160],
                }
            )
    return {
        "title_counter": title_counter,
        "description_counter": description_counter,
        "title_examples": title_examples,
        "description_examples": description_examples,
    }


def summarize_aim(db_path: Path, limit: int) -> Dict[str, Any]:
    if not db_path.exists():
        return {}
    with sqlite3.connect(str(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        row = cursor.execute(
            "SELECT id FROM experiment WHERE name = ? LIMIT 1",
            ("youtube-ai-v2",),
        ).fetchone()
        if not row:
            return {}
        experiment_id = row["id"]
        aggregates = cursor.execute(
            "SELECT COUNT(*) AS total_runs, MIN(created_at) AS earliest, MAX(created_at) AS latest "
            "FROM run WHERE experiment_id = ?",
            (experiment_id,),
        ).fetchone()
        recent_rows = cursor.execute(
            "SELECT hash, created_at, name FROM run WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
            (experiment_id, limit),
        ).fetchall()
        return {
            "total_runs": aggregates["total_runs"] if aggregates else 0,
            "earliest_run": aggregates["earliest"] if aggregates else None,
            "latest_run": aggregates["latest"] if aggregates else None,
            "recent_runs": [
                {"hash": record["hash"], "created_at": record["created_at"], "name": record["name"]}
                for record in recent_rows
            ],
        }


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    runs_dir = Path(args.runs_dir)
    aim_db = Path(args.aim_db)
    entries = load_metadata(runs_dir)
    findings = detect_terms(entries)
    total_entries = len(entries)
    title_flags = len(findings["title_examples"])
    description_flags = len(findings["description_examples"])
    report: Dict[str, Any] = {
        "tone_report": {
            "runs_scanned": total_entries,
            "title_flagged_runs": title_flags,
            "description_flagged_runs": description_flags,
            "flagged_title_ratio": round(title_flags / total_entries, 3) if total_entries else 0.0,
            "flagged_description_ratio": round(description_flags / total_entries, 3) if total_entries else 0.0,
            "title_term_counts": dict(findings["title_counter"].most_common()),
            "description_term_counts": dict(findings["description_counter"].most_common()),
            "title_examples": findings["title_examples"][: args.limit],
            "description_examples": findings["description_examples"][: args.limit],
            "aim_tracker": summarize_aim(aim_db, args.limit),
        }
    }
    lengths = [entry["title_length"] for entry in entries]
    if lengths:
        report["tone_report"]["title_length_avg"] = round(sum(lengths) / len(lengths), 1)
        report["tone_report"]["title_length_max"] = max(lengths)
    return report


def main() -> None:
    args = parse_args()
    report = build_report(args)
    text = yaml.safe_dump(report, sort_keys=False, allow_unicode=True)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
