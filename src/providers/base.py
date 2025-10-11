from typing import Any, Iterable, Protocol


class Provider(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def execute(self, **kwargs: Any) -> Any: ...


def execute_with_fallback(providers: Iterable[Provider], **kwargs: Any) -> Any:
    for provider in providers:
        if provider.is_available():
            return provider.execute(**kwargs)
    raise RuntimeError("No providers available")
