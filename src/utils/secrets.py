import os
from typing import Iterable


def load_secret_values(key_basename: str, *, max_keys: int = 10, extra_dirs: Iterable = None) -> list[str]:
    if not key_basename:
        return []
    values: list[str] = []
    prefix = key_basename.upper()
    for index in range(1, max_keys + 1):
        suffix = f"_{index}" if index > 1 else ""
        value = os.getenv(f"{prefix}{suffix}")
        if value and value not in values:
            values.append(value)
    return values
