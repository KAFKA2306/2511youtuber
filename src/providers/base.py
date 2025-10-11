from abc import ABC, abstractmethod
from typing import Any, List

from src.utils.logger import get_logger

logger = get_logger(__name__)


class Provider(ABC):
    name: str
    priority: int = 999

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        pass


class ProviderChain:
    def __init__(self, providers: List[Provider]):
        self.providers = sorted(providers, key=lambda p: p.priority)
        self.logger = get_logger(self.__class__.__name__)

    def execute(self, **kwargs) -> Any:
        last_error = None

        for provider in self.providers:
            if not provider.is_available():
                self.logger.debug(f"Provider {provider.name} not available, skipping")
                continue

            try:
                self.logger.info(f"Trying provider {provider.name}")
                result = provider.execute(**kwargs)
                self.logger.info(f"Provider {provider.name} succeeded")
                return result
            except Exception as e:
                self.logger.warning(f"Provider {provider.name} failed", error=str(e))
                last_error = e
                continue

        raise AllProvidersFailedError(f"All providers failed. Last error: {last_error}")


class AllProvidersFailedError(Exception):
    pass
