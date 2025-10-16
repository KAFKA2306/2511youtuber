import pytest

from src.providers.news import GeminiNewsProvider, PerplexityNewsProvider

pytestmark = pytest.mark.e2e


class TestNewsProviders:
    def test_gemini_availability(self):
        gemini = GeminiNewsProvider()
        assert gemini.is_available()

    def test_perplexity_availability(self):
        perplexity = PerplexityNewsProvider()
        assert perplexity.is_available()

    def test_gemini_news_collection(self):
        gemini = GeminiNewsProvider()
        if not gemini.is_available():
            pytest.skip("GEMINI_API_KEY not set")
        news = gemini.execute(query="日本の最新金融ニュース", count=2)
        assert len(news) == 2
        assert all(item.title for item in news)
        assert all(item.url.startswith("http") for item in news)
        assert all(item.summary for item in news)
        for item in news:
            print(f"\nGot real news: {item.title[:60]}")
            print(f"  URL: {item.url}")
            print(f"  Published: {item.published_at}")

    def test_perplexity_news_collection(self):
        perplexity = PerplexityNewsProvider()
        if not perplexity.is_available():
            pytest.skip("PERPLEXITY_API_KEY not set")
        news = perplexity.execute(query="日本の最新金融ニュース", count=2)
        assert len(news) == 2
        assert all(item.title for item in news)
