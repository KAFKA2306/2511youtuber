import types

import pytest

from src.providers.llm import GeminiProvider


pytestmark = pytest.mark.unit


class DummyResponse(types.SimpleNamespace):
    pass


def _dummy_completion_factory(record):
    def _completion(*args, **kwargs):
        record.append(kwargs.get("api_key"))
        return DummyResponse(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content="dummy")
                )
            ]
        )

    return _completion


def test_gemini_provider_rotates_keys(monkeypatch):
    for index in range(1, 10):
        suffix = "" if index == 1 else f"_{index}"
        monkeypatch.delenv(f"GEMINI_API_KEY{suffix}", raising=False)

    monkeypatch.setenv("GEMINI_API_KEY", "key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key-2")
    monkeypatch.setenv("GEMINI_API_KEY_3", "key-3")

    calls: list[str] = []
    monkeypatch.setattr(
        "src.providers.llm.litellm.completion",
        _dummy_completion_factory(calls),
    )

    provider = GeminiProvider(model="gemini/test", temperature=0.0, max_tokens=10)

    for _ in range(5):
        provider.execute(prompt="test")

    assert calls[:5] == ["key-1", "key-2", "key-3", "key-1", "key-2"]
