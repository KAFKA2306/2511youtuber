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
        "flagged_terms": flagged_terms,
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


def load_tone_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        return {}
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    metadata_cfg = config.get("steps", {}).get("metadata", {})
    return metadata_cfg.get("tone", {}) if isinstance(metadata_cfg, dict) else {}


def apply_tone(text: str, tone_cfg: Dict[str, Any], field: str) -> str:
    replacements = tone_cfg.get("replacements", {})
    disallowed = tone_cfg.get(f"{field}_disallowed_terms", [])
    result = text
    if isinstance(replacements, dict):
        for source, target in replacements.items():
            result = result.replace(str(source), str(target))
    for term in disallowed:
        term_str = str(term)
        if term_str not in replacements:
            result = result.replace(term_str, "")
    return result.strip()


def simulate_tone(entries: List[Dict[str, Any]], tone_cfg: Dict[str, Any], flagged_terms: List[str]) -> Dict[str, Any]:
    if not tone_cfg:
        return {}
    before_title = sum(1 for entry in entries if any(term in entry["title"] for term in flagged_terms))
    before_desc = sum(1 for entry in entries if any(term in entry["description"] for term in flagged_terms))

    after_title_counter: Counter[str] = Counter()
    after_desc_counter: Counter[str] = Counter()
    after_title_samples: List[Dict[str, Any]] = []
    after_desc_samples: List[Dict[str, Any]] = []

    for entry in entries:
        sanitized_title = apply_tone(entry["title"], tone_cfg, "title")
        sanitized_desc = apply_tone(entry["description"], tone_cfg, "description")
        title_hits = sorted({term for term in flagged_terms if term in sanitized_title})
        desc_hits = sorted({term for term in flagged_terms if term in sanitized_desc})
        for term in title_hits:
            after_title_counter[term] += 1
        for term in desc_hits:
            after_desc_counter[term] += 1
        if title_hits:
            after_title_samples.append(
                {
                    "run_id": entry["run_id"],
                    "title_before": entry["title"],
                    "title_after": sanitized_title,
                    "terms_before": [term for term in flagged_terms if term in entry["title"]],
                    "terms_after": title_hits,
                }
            )
        if desc_hits:
            after_desc_samples.append(
                {
                    "run_id": entry["run_id"],
                    "excerpt_before": entry["description"][:160],
                    "excerpt_after": sanitized_desc[:160],
                    "terms_before": [term for term in flagged_terms if term in entry["description"]],
                    "terms_after": desc_hits,
                }
            )

    total = len(entries) or 1
    return {
        "title_flagged_runs": len(after_title_samples),
        "description_flagged_runs": len(after_desc_samples),
        "flagged_title_ratio": round(len(after_title_samples) / total, 3),
        "flagged_description_ratio": round(len(after_desc_samples) / total, 3),
        "title_term_counts": dict(after_title_counter.most_common()),
        "description_term_counts": dict(after_desc_counter.most_common()),
        "title_samples": after_title_samples[:10],
        "description_samples": after_desc_samples[:10],
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
            "tone_config_path": "config/default.yaml",
        }
    }
    lengths = [entry["title_length"] for entry in entries]
    if lengths:
        report["tone_report"]["title_length_avg"] = round(sum(lengths) / len(lengths), 1)
        report["tone_report"]["title_length_max"] = max(lengths)
    tone_cfg = load_tone_config(Path("config/default.yaml"))
    if tone_cfg:
        report["tone_report"]["simulated_tone"] = simulate_tone(entries, tone_cfg, findings["flagged_terms"])
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
