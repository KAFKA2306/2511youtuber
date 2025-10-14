import json as json_module

import pytest

from src.providers.base import AllProvidersFailedError, Provider, ProviderChain
from src.providers.news import PerplexityNewsProvider

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


class TestPerplexityNewsProvider:

    def test_execute_includes_recency_filter(self, monkeypatch):
        captured_payload: dict = {}

        def fake_load_secret_values(key: str):
            assert key == "PERPLEXITY_API_KEY"
            return ["dummy-key"]

        def fake_post(url, headers=None, json=None):  # noqa: A002 - match requests.post signature
            captured_payload["json"] = json

            class DummyResponse:

                @staticmethod
                def raise_for_status() -> None:
                    return None

                @staticmethod
                def json() -> dict:
                    return {
                        "choices": [
                            {
                                "message": {
                                    "content": json_module.dumps(
                                        [
                                            {
                                                "title": "Sample",
                                                "summary": "Summary",
                                                "url": "https://example.com",
                                                "published_at": "2024-05-01T00:00:00Z",
                                            }
                                        ]
                                    )
                                }
                            }
                        ]
                    }

            return DummyResponse()

        monkeypatch.setattr("src.providers.news.load_secret_values", fake_load_secret_values)
        monkeypatch.setattr("src.providers.news.requests.post", fake_post)

        provider = PerplexityNewsProvider(search_recency_filter="week")

        result = provider.execute(query="test", count=1)

        assert len(result) == 1
        assert captured_payload["json"]["search_recency_filter"] == "week"
