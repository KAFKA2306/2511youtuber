from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_path(value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


@lru_cache
def load_discord_config() -> dict[str, Any]:
    config_path = Path(os.getenv("DISCORD_CONFIG_PATH", str(resolve_path("config/discord.yaml"))))
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))
