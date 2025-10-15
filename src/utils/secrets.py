import os
from pathlib import Path
from typing import Iterable


def load_secret_values(key_basename: str, *, max_keys: int = 10, extra_dirs: Iterable | None = None) -> list[str]:
    if not key_basename:
        return []

    values: list[str] = []
    prefix = key_basename.upper()
    keys = [f"{prefix}{'' if index == 1 else f'_{index}'}" for index in range(1, max_keys + 1)]

    for env_key in keys:
        value = os.getenv(env_key)
        if value and value not in values:
            values.append(value)

    env_files = [Path(__file__).resolve().parents[2] / "config" / ".env"]
    env_files.extend(
        (candidate / ".env" if candidate.is_dir() else candidate) for candidate in map(Path, extra_dirs or ())
    )

    for env_file in env_files:
        if not env_file.exists():
            continue
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            if key.strip().upper() in keys and value and value.strip() not in values:
                values.append(value.strip())

    return values
