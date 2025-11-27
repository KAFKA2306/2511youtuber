"""
Test configuration - minimal utilities only.
All tests use real APIs, real data, real system components.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture(autouse=True)
def slow_down_tests():
    """Add a delay between tests to avoid API rate limits."""
    yield
    print("\nSleeping 10s for API rate limits...")
    time.sleep(10)


@pytest.fixture
def temp_run_dir(tmp_path: Path) -> Iterator[Path]:
    """Temporary run directory for test artifacts."""
    run_dir = tmp_path / "test_runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    yield run_dir
    # Cleanup after test
    if run_dir.exists():
        shutil.rmtree(run_dir, ignore_errors=True)


def assert_file_exists_with_content(path: Path, min_size_kb: int = 1) -> None:
    """Assert file exists and has reasonable content."""
    assert path.exists(), f"File not found: {path}"
    size_kb = path.stat().st_size / 1024
    assert size_kb >= min_size_kb, f"File too small: {size_kb:.1f}KB < {min_size_kb}KB"
