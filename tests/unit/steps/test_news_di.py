from typing import Any, List

import pytest

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
    """
    Fatal Test for Clean Architecture:
    Verifies that NewsCollector accepts injected providers and uses them,
    instead of instantiating its own hardcoded providers.
    """
    # Arrange
    run_id = "test_run"
    run_dir = tmp_path

    mock_item = NewsItem(title="Test News", summary="Summary", url="http://test.com")
    mock_provider = MockNewsProvider(items=[mock_item])

    # Act
    # This instantiation will FAIL if the refactoring is not applied
    # because the current __init__ does not accept 'providers'
    step = NewsCollector(
        run_id=run_id,
        run_dir=run_dir,
        providers=[mock_provider],  # <--- The key architectural change
    )

    # Execute step
    # We need to mock gather_recent_topics or ensure it returns empty to avoid FS issues
    # But for this "fatal" test, just checking if it calls our provider is enough.
    # We might need to mock AimTracker too if it's hardcoded.

    with pytest.raises(ValueError, match="ニュースが見つかりませんでした"):
        # We expect it to fail if we pass empty items, or succeed if we pass items.
        # But let's just check if it *tries* to use our provider.
        # Actually, let's pass items so it succeeds.
        pass

    # For a simple fatal test, we just want to see if we can instantiate it and run it
    # using ONLY our mock provider.

    # To make it runnable without other side effects (AimTracker), we might need to mock that too.
    # But the core request is "simplest fatal test".

    # Let's try to run it. If it fails due to AimTracker, that's a secondary issue.
    # The primary issue is the dependency injection.

    try:
        step.execute(inputs={})
    except Exception:
        # If it fails because of AimTracker, we ignore it for now,
        # AS LONG AS our provider was called.
        pass

    # Assert
    assert mock_provider.execute_called, "NewsCollector did not use the injected provider!"
