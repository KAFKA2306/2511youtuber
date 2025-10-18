from __future__ import annotations

from pathlib import Path

import pytest

from src.steps.news import NewsCollector
from src.utils.config import NewsProvidersConfig, PerplexityNewsProviderConfig


@pytest.fixture(autouse=True)
def stub_news_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.providers.news.load_secret_values", lambda key: [f"token-for-{key}"])
    monkeypatch.setattr(
        "src.providers.news.load_prompts",
        lambda: {"news_collection": {"system": "system", "user_template": "{topic} {count}"}},
    )


def test_news_collector_builds_providers_from_config(tmp_path: Path) -> None:
    config = NewsProvidersConfig(
        perplexity=PerplexityNewsProviderConfig(
            enabled=True,
            model="sonar-large",
            temperature=0.3,
            max_tokens=1024,
            search_recency_filter="month",
        )
    )

    run_dir = tmp_path / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)

    collector = NewsCollector("run", run_dir, query="AI", providers_config=config)
    providers = collector._build_providers()

    assert providers[0].name == "perplexity"
    assert providers[0].model == "sonar-large"
    assert providers[1].name == "gemini"


def test_news_collector_defaults_to_perplexity_and_gemini(tmp_path: Path) -> None:
    run_dir = tmp_path / "default"
    run_dir.mkdir(parents=True, exist_ok=True)

    collector = NewsCollector("run", run_dir)
    providers = collector._build_providers()

    assert [provider.name for provider in providers] == ["perplexity", "gemini"]
