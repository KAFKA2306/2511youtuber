import pytest
from src.providers.base import Provider, ProviderChain, AllProvidersFailedError

pytestmark = pytest.mark.unit


class MockProvider(Provider):
    def __init__(self, name: str, priority: int, available: bool = True, should_fail: bool = False):
        self.name = name
        self.priority = priority
        self._available = available
        self._should_fail = should_fail

    def is_available(self) -> bool:
        return self._available

    def execute(self, **kwargs):
        if self._should_fail:
            raise Exception(f"{self.name} failed")
        return f"{self.name}_result"


class TestProviderChain:
    def test_first_provider_succeeds(self):
        providers = [
            MockProvider("primary", priority=1),
            MockProvider("secondary", priority=2),
        ]
        chain = ProviderChain(providers)
        result = chain.execute()
        assert result == "primary_result"

    def test_fallback_to_second_provider(self):
        providers = [
            MockProvider("primary", priority=1, should_fail=True),
            MockProvider("secondary", priority=2),
        ]
        chain = ProviderChain(providers)
        result = chain.execute()
        assert result == "secondary_result"

    def test_skip_unavailable_provider(self):
        providers = [
            MockProvider("primary", priority=1, available=False),
            MockProvider("secondary", priority=2),
        ]
        chain = ProviderChain(providers)
        result = chain.execute()
        assert result == "secondary_result"

    def test_all_providers_fail(self):
        providers = [
            MockProvider("primary", priority=1, should_fail=True),
            MockProvider("secondary", priority=2, should_fail=True),
        ]
        chain = ProviderChain(providers)
        with pytest.raises(AllProvidersFailedError):
            chain.execute()

    def test_priority_ordering(self):
        providers = [
            MockProvider("low_priority", priority=10),
            MockProvider("high_priority", priority=1),
            MockProvider("medium_priority", priority=5),
        ]
        chain = ProviderChain(providers)
        result = chain.execute()
        assert result == "high_priority_result"
