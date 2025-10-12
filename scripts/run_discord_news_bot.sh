#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${PROJECT_ROOT}/config/.env" ]]; then
  set -a
  source "${PROJECT_ROOT}/config/.env"
  set +a
fi

cd "${PROJECT_ROOT}"

if command -v uv >/dev/null 2>&1; then
  exec uv run python scripts/discord_news_bot.py
else
  exec python scripts/discord_news_bot.py
fi
