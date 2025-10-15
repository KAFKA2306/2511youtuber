import json
from pathlib import Path
from typing import Dict, TypeVar

from src.models import Script

T = TypeVar("T")


def load_json(path: Path, default: T = None) -> Dict | T:
    if not path.exists():
        return default or {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_script(path: Path) -> Script:
    return Script(**load_json(path))


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def validate_input_files(inputs: Dict[str, Path], *keys: str) -> None:
    for key in keys:
        path = inputs.get(key)
        if not path or not Path(path).exists():
            raise ValueError(f"Required input '{key}' not found")
