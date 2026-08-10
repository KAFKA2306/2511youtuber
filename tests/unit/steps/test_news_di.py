from typing import Any, List

from src.models import NewsItem
from src.steps.news import NewsCollector


class MockNewsProvider:
    name = "mock_provider"

    def __init__(self, items: List[NewsItem] | None = None):
        self.items = items or []
        self.execute_called = False

    def is_available(self) -> bool:
        return True

    def execute(self, **kwargs: Any) -> List[NewsItem]:
        self.execute_called = True
        return self.items


def test_news_collector_dependency_injection(tmp_path):
    """NewsCollector must retrieve candidates through the injected provider."""
    mock_item = NewsItem(title="Test News", summary="Summary", url="http://test.com")
    mock_provider = MockNewsProvider(items=[mock_item])
    step = NewsCollector(
        run_id="test_run",
        run_dir=tmp_path,
        providers=[mock_provider],
        query_buckets={"broad": "finance"},
        fetch_count=1,
        final_count=1,
    )

    # The focused CI intentionally does not install the optional Aim runtime.
    # Retrieval and deterministic selection must still occur before tracking is entered.
    try:
        step.execute(inputs={})
    except ModuleNotFoundError as exc:
        assert exc.name == "aim"

    assert mock_provider.execute_called, "NewsCollector did not use the injected provider"
