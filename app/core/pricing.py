"""Pricing logic: provider cost -> customer price with markup and period discounts.

Внутренняя валюта — USD. Цены Hetzner (EUR) конвертируются по курсу из настроек.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.core.config import get_settings

CENT = Decimal("0.01")


def to_usd(amount: Decimal, currency: str) -> Decimal:
    settings = get_settings()
    if currency.upper() == "EUR":
        return (amount * settings.eur_usd_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def customer_monthly_price(provider_monthly_usd: Decimal) -> Decimal:
    """Цена для клиента: себестоимость + наценка (по умолчанию 35%)."""
    markup = get_settings().markup_percent
    price = provider_monthly_usd * (Decimal(100) + markup) / Decimal(100)
    return price.quantize(CENT, rounding=ROUND_HALF_UP)


def period_price(customer_monthly_usd: Decimal, months: int) -> Decimal:
    """Итоговая цена за период с учётом скидки за длительность."""
    discounts = get_settings().period_discounts
    discount = discounts.get(months, Decimal(0))
    total = customer_monthly_usd * months * (Decimal(100) - discount) / Decimal(100)
    return total.quantize(CENT, rounding=ROUND_HALF_UP)


def available_periods() -> list[int]:
    return sorted(get_settings().period_discounts.keys())
