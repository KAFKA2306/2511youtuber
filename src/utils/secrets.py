"""Utilities for loading sensitive configuration from environment variables or secret files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Set

_ENV_FILE_PATHS = [
    Path(__file__).resolve().parents[2] / "config" / ".env",
]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SECRET_DIRS = [
    Path("/run/secrets"),
    Path("/etc/secrets"),
    Path("/var/openai/secrets"),
    Path("/var/opt/secrets"),
    Path("/workspace/.secrets"),
    Path.home() / ".secrets",
    _REPO_ROOT / ".secrets",
    _REPO_ROOT / "secrets",
    _REPO_ROOT / "config",
]


def _normalise_directory(path: str | os.PathLike[str] | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path).expanduser()
    try:
        candidate = candidate.resolve()
    except OSError:
        return None
    return candidate if candidate.exists() else None


def _candidate_secret_directories(extra_dirs: Iterable[Path] | None = None, env_prefix: str = "") -> List[Path]:
    directories: List[Path] = []

    # Environment overrides take precedence
    env_keys = [
        f"{env_prefix}_DIR" if env_prefix else "GEMINI_SECRETS_DIR",
        f"{env_prefix}_DIRECTORY" if env_prefix else "GEMINI_SECRETS_DIRECTORY",
        "SECRETS_DIR",
        "SECRETS_DIRECTORY",
    ]
    for key in env_keys:
        value = os.getenv(key)
        directory = _normalise_directory(value)
        if directory and directory not in directories:
            directories.append(directory)

    if extra_dirs:
        for directory in extra_dirs:
            try:
                directory = directory.resolve()
            except OSError:
                continue
            if directory.exists() and directory not in directories:
                directories.append(directory)

    for default_dir in _DEFAULT_SECRET_DIRS:
        try:
            resolved = default_dir.resolve()
        except OSError:
            continue
        if resolved.exists() and resolved not in directories:
            directories.append(resolved)

    return directories


def _candidate_file_names(base_name: str, index: int) -> List[str]:
    suffix = f"_{index}" if index > 1 else ""
    base_variants = {
        f"{base_name}{suffix}",
        f"{base_name.lower()}{suffix}",
        f"{base_name.upper()}{suffix}",
    }
    file_names: Set[str] = set()
    for variant in base_variants:
        file_names.add(variant)
        for extension in ("", ".txt", ".secret", ".key"):
            if extension:
                file_names.add(f"{variant}{extension}")
    return list(file_names)


def _read_secret_file(path: Path) -> list[str]:
    values: list[str] = []
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return values

    for line in content.splitlines():
        value = line.strip()
        if value:
            values.append(value)

    if not values:
        stripped = content.strip()
        if stripped:
            values.append(stripped)

    return values


def load_secret_values(
    key_basename: str,
    *,
    max_keys: int = 10,
    extra_dirs: Iterable[Path] | None = None,
) -> list[str]:
    """Return ordered secret values sourced from the environment or secret files.

    The ``key_basename`` should correspond to the environment variable prefix, e.g.
    ``"GEMINI_API_KEY"``. Environment variables (including ``*_FILE`` and
    ``*_PATH`` indirections) are considered before scanning well-known secret
    directories for files matching typical naming conventions.
    """

    if not key_basename:
        return []

    env_prefix = key_basename.upper()
    values: list[str] = []
    seen: Set[str] = set()

    def _add(value: str | None) -> None:
        if not value:
            return
        if value in seen:
            return
        seen.add(value)
        values.append(value)

    # 1. Direct environment variables and file/path indirections
    for index in range(1, max_keys + 1):
        suffix = f"_{index}" if index > 1 else ""
        env_name = f"{env_prefix}{suffix}"
        _add(os.getenv(env_name))

        file_env = os.getenv(f"{env_name}_FILE") or os.getenv(f"{env_name}_PATH")
        if file_env:
            file_path = _normalise_directory(file_env)
            if file_path and file_path.is_file():
                for secret in _read_secret_file(file_path):
                    _add(secret)

    # 2. Scan directories for files containing the secret
    directories = _candidate_secret_directories(extra_dirs, env_prefix)
    for directory in directories:
        if not directory.is_dir():
            continue
        for index in range(1, max_keys + 1):
            for file_name in _candidate_file_names(env_prefix, index):
                file_path = directory / file_name
                if file_path.is_file():
                    for secret in _read_secret_file(file_path):
                        _add(secret)

    # 3. Parse shared .env files when no values have been discovered yet
    if not values:
        for env_path in _ENV_FILE_PATHS:
            if not env_path.is_file():
                continue
            entries = _read_env_mapping(env_path)
            for index in range(1, max_keys + 1):
                suffix = f"_{index}" if index > 1 else ""
                key = f"{env_prefix}{suffix}"
                _add(entries.get(key))

    return values


def _read_env_mapping(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return mapping

    for line in content.splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value and key not in mapping:
            mapping[key] = value

    return mapping
