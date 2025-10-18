from __future__ import annotations

import pytest

from src.providers.base import AllProvidersFailedError, ProviderChain, execute_with_fallback


class DummyProvider:
    def __init__(
        self,
        name: str,
        *,
        available: bool = True,
        result: object | None = None,
        priority: int = 0,
        should_fail: bool = False,
    ) -> None:
        self.name = name
        self._available = available
        self._result = result if result is not None else name
        self.priority = priority
        self._should_fail = should_fail
        self.calls: int = 0

    def is_available(self) -> bool:
        return self._available

    def execute(self, **_: object) -> object:
        self.calls += 1
        if self._should_fail:
            raise RuntimeError(f"{self.name} failed")
        return self._result


def test_provider_chain_prefers_highest_priority() -> None:
    low = DummyProvider("low", priority=1, result="low")
    high = DummyProvider("high", priority=10, result="high")

    chain = ProviderChain([low, high])
    result = chain.execute()

    assert result == "high"
    assert high.calls == 1
    assert low.calls == 0


def test_execute_with_fallback_skips_unavailable_and_recovers() -> None:
    providers = [
        DummyProvider("first", available=False),
        DummyProvider("second", should_fail=True),
        DummyProvider("third", result="ok"),
    ]

    result = execute_with_fallback(providers)

    assert result == "ok"
    assert providers[0].calls == 0
    assert providers[1].calls == 1
    assert providers[2].calls == 1


def test_provider_chain_raises_with_all_failures() -> None:
    providers = [
        DummyProvider("one", should_fail=True),
        DummyProvider("two", should_fail=True),
    ]

    chain = ProviderChain(providers)

    with pytest.raises(AllProvidersFailedError) as excinfo:
        chain.execute()

    assert excinfo.value.providers == ["one", "two"]
    assert set(excinfo.value.errors) == {"one", "two"}
