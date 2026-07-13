"""Catalog: live prices from providers with markup, cached in memory.

Кэш обновляется раз в 10 минут, чтобы не дёргать API провайдеров на каждый клик.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from loguru import logger

from app.core.pricing import customer_monthly_price
from app.models.base import Provider
from app.providers import Image, Location, Plan, available_providers, get_provider

CACHE_TTL_SECONDS = 600


@dataclass
class ProviderCatalog:
    locations: list[Location] = field(default_factory=list)
    plans: list[Plan] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)
    fetched_at: float = 0.0


_cache: dict[Provider, ProviderCatalog] = {}


async def get_catalog(provider: Provider, force: bool = False) -> ProviderCatalog:
    cached = _cache.get(provider)
    if cached and not force and time.monotonic() - cached.fetched_at < CACHE_TTL_SECONDS:
        return cached

    client = get_provider(provider)
    try:
        catalog = ProviderCatalog(
            locations=await client.get_locations(),
            plans=await client.get_plans(),
            images=await client.get_images(),
            fetched_at=time.monotonic(),
        )
    except Exception as exc:
        logger.error("Failed to refresh {} catalog: {}", provider.value, exc)
        if cached:
            return cached  # отдаём устаревший кэш, лучше чем ничего
        raise
    _cache[provider] = catalog
    logger.debug(
        "Catalog refreshed for {}: {} locations, {} plans, {} images",
        provider.value, len(catalog.locations), len(catalog.plans), len(catalog.images),
    )
    return catalog


def plans_for_location(catalog: ProviderCatalog, location_id: str) -> list[Plan]:
    plans = [
        p for p in catalog.plans
        if not p.locations or location_id in p.locations
    ]
    return sorted(plans, key=lambda p: p.monthly_cost_usd)


def find_plan(catalog: ProviderCatalog, plan_id: str) -> Plan | None:
    return next((p for p in catalog.plans if p.id == plan_id), None)


def find_location(catalog: ProviderCatalog, location_id: str) -> Location | None:
    return next((loc for loc in catalog.locations if loc.id == location_id), None)


def find_image(catalog: ProviderCatalog, image_id: str) -> Image | None:
    return next((img for img in catalog.images if img.id == image_id), None)


def plan_customer_price(plan: Plan):  # -> Decimal
    """Цена плана для клиента (с наценкой), USD/мес."""
    return customer_monthly_price(plan.monthly_cost_usd)


def configured_providers() -> list[Provider]:
    return available_providers()
