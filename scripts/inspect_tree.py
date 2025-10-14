#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"


@dataclass(frozen=True)
class FileStats:
    path: Path
    total_loc: int
    code_loc: int
    module: str | None
    imports: Set[str]


def python_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def module_name(path: Path) -> str | None:
    try:
        rel = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return None
    parts = list(rel.with_suffix("").parts)
    if not parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)


def count_loc(path: Path) -> Tuple[int, int]:
    total = 0
    code = 0
    for raw in path.read_text().splitlines():
        total += 1
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            code += 1
    return total, code


def resolve_relative(module: str, level: int, target: str | None) -> str | None:
    if not module:
        return None
    parts = module.split(".")
    if level > len(parts):
        return None
    base = parts[: len(parts) - level]
    if target:
        base.extend(target.split("."))
    if not base:
        return None
    return ".".join(base)


def parse_imports(path: Path, module: str | None) -> Set[str]:
    content = path.read_text()
    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError:
        return set()
    found: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level:
                resolved = resolve_relative(module or "", node.level, node.module)
                if resolved:
                    found.add(resolved)
            elif target:
                found.add(target)
    return found


def gather_stats(root: Path) -> List[FileStats]:
    stats: List[FileStats] = []
    for path in python_files(root):
        total_loc, code_loc = count_loc(path)
        mod_name = module_name(path)
        imports = parse_imports(path, mod_name)
        stats.append(FileStats(path=path, total_loc=total_loc, code_loc=code_loc, module=mod_name, imports=imports))
    return stats


def summarise_by_directory(stats: Iterable[FileStats], base: Path) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = defaultdict(lambda: {"files": 0, "total_loc": 0, "code_loc": 0})
    for item in stats:
        rel = item.path.relative_to(base)
        top = rel.parts[0] if len(rel.parts) > 1 else rel.parts[0]
        bucket = summary[top]
        bucket["files"] += 1
        bucket["total_loc"] += item.total_loc
        bucket["code_loc"] += item.code_loc
    return dict(sorted(summary.items(), key=lambda kv: kv[1]["total_loc"], reverse=True))


def mark_unused_modules(stats: Iterable[FileStats]) -> List[FileStats]:
    module_lookup: Dict[str, FileStats] = {}
    imported_modules: Set[str] = set()
    for item in stats:
        if item.module:
            module_lookup[item.module] = item
        imported_modules.update(item.imports)
    unused: List[FileStats] = []
    for module, info in module_lookup.items():
        if info.code_loc == 0:
            continue
        if module.startswith("scripts."):
            continue
        if module == "src.main":
            continue
        if module not in imported_modules and not module.endswith(".__main__"):
            unused.append(info)
    unused.sort(key=lambda item: item.code_loc, reverse=True)
    return unused


def print_report(stats: List[FileStats], base: Path) -> None:
    total_loc = sum(item.total_loc for item in stats)
    total_code = sum(item.code_loc for item in stats)
    print(f"Project LOC (total/code): {total_loc}/{total_code}")

    summary = summarise_by_directory(stats, base)
    print("\nBy directory (sorted by LOC):")
    for name, bucket in summary.items():
        print(f"  {name:15s} files={bucket['files']:3d} total={bucket['total_loc']:4d} code={bucket['code_loc']:4d}")

    heaviest = sorted(stats, key=lambda item: item.code_loc, reverse=True)[:10]
    print("\nTop 10 modules by code LOC:")
    for item in heaviest:
        rel = item.path.relative_to(PROJECT_ROOT)
        print(f"  {rel} ({item.code_loc} code LOC / {item.total_loc} total)")

    unused = mark_unused_modules(stats)
    if unused:
        print("\nPotentially unused modules (no imports inside project):")
        for item in unused[:10]:
            rel = item.path.relative_to(PROJECT_ROOT)
            print(f"  {rel} ({item.code_loc} code LOC)")
    else:
        print("\nNo unused modules detected via import scan.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise project LOC and highlight unused modules.")
    parser.add_argument("root", nargs="?", default=str(SRC_ROOT), help="Path to inspect (default: src/)")
    args = parser.parse_args()

    root_path = Path(args.root).resolve()
    if not root_path.exists():
        raise SystemExit(f"Path not found: {root_path}")

    stats = gather_stats(root_path)
    if not stats:
        raise SystemExit("No Python files found.")

    print_report(stats, root_path)


if __name__ == "__main__":
    main()
