"""Provider registry: single place to get a configured provider client."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.models.base import Provider
from app.providers.base import BaseProvider, Image, Location, Plan, ProviderError, ServerInfo
from app.providers.hetzner import HetznerProvider
from app.providers.vultr import VultrProvider

__all__ = [
    "BaseProvider",
    "Image",
    "Location",
    "Plan",
    "ProviderError",
    "ServerInfo",
    "get_provider",
    "available_providers",
]


@lru_cache
def get_provider(provider: Provider) -> BaseProvider:
    settings = get_settings()
    if provider is Provider.VULTR:
        return VultrProvider(settings.vultr_api_key)
    if provider is Provider.HETZNER:
        return HetznerProvider(settings.hetzner_api_token)
    raise ValueError(f"Unknown provider: {provider}")


def available_providers() -> list[Provider]:
    """Провайдеры, для которых заданы API-ключи."""
    return [p for p in Provider if get_provider(p).is_configured]
