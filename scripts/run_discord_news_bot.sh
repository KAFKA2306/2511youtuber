#!/usr/bin/env bash
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
exec uv run python scripts/discord_news_bot.py
