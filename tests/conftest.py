import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_run_dir():
    temp_dir = tempfile.mkdtemp(prefix="test_run_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_news_path():
    return Path(__file__).parent / "fixtures" / "sample_news.json"


@pytest.fixture
def sample_script_path():
    return Path(__file__).parent / "fixtures" / "sample_script.json"


@pytest.fixture
def test_run_id():
    return "test_20251010_120000"
