from typing import Any, Iterable, Protocol, Sequence


def has_credentials(provider: object) -> bool:
    return bool(getattr(provider, "api_keys", ()))


class Provider(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def execute(self, **kwargs: Any) -> Any: ...


class AllProvidersFailedError(RuntimeError):
    def __init__(self, providers: Sequence[str], errors: dict[str, Exception]):
        message = ", ".join(providers) or "no providers"
        super().__init__(f"All providers failed: {message}")
        self.providers = providers
        self.errors = errors


class ProviderChain:
    def __init__(self, providers: Iterable[Provider]):
        self.providers = sorted(
            providers,
            key=lambda provider: getattr(provider, "priority", 0),
            reverse=True,
        )

    def execute(self, **kwargs: Any) -> Any:
        errors: dict[str, Exception] = {}
        for provider in self.providers:
            if not provider.is_available():
                continue
            try:
                return provider.execute(**kwargs)
            except Exception as exc:  # noqa: BLE001 - bubble up aggregated failure
                errors[provider.name] = exc
        raise AllProvidersFailedError([p.name for p in self.providers], errors)


def execute_with_fallback(providers: Iterable[Provider], **kwargs: Any) -> Any:
    return ProviderChain(providers).execute(**kwargs)
