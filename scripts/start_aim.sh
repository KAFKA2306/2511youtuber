#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"
nohup uv run python scripts/import_to_aim.py >/dev/null 2>&1 && nohup aim up --host 0.0.0.0 --port 43800 >/dev/null 2>&1 &
