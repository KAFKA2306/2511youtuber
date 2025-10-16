import pytest

from src.providers.base import execute_with_fallback
from src.providers.news import GeminiNewsProvider, PerplexityNewsProvider

pytestmark = pytest.mark.e2e


class TestNewsFallback:
    def test_fallback_chain(self):
        providers = [PerplexityNewsProvider(), GeminiNewsProvider()]
        news = execute_with_fallback(providers, query="日本の最新金融ニュース", count=2)
        assert len(news) == 2
        assert all(item.title for item in news)
