from __future__ import annotations

import hashlib
from pathlib import Path


CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
DEFAULT_PROMPTS_PATH = CONFIG_DIR / "prompts.yaml"
NEWS_SELECTION_PROMPTS_PATH = CONFIG_DIR / "news_selection.yaml"


def prompt_bundle_version(prompts_path: str | Path | None = None) -> str:
    """Return an immutable content version for the prompt bundle."""
    if prompts_path is not None:
        paths = [Path(prompts_path)]
    else:
        paths = [DEFAULT_PROMPTS_PATH, NEWS_SELECTION_PROMPTS_PATH]

    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"
