from __future__ import annotations

import hashlib
from pathlib import Path


DEFAULT_PROMPTS_PATH = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"


def prompt_bundle_version(prompts_path: str | Path | None = None) -> str:
    """Return an immutable content version for the prompt bundle."""
    path = Path(prompts_path) if prompts_path is not None else DEFAULT_PROMPTS_PATH
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
