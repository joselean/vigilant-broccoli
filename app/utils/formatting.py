"""HTML formatting helpers for Telegram messages."""
from __future__ import annotations

import html
from datetime import datetime
from decimal import Decimal


def esc(text: str | None) -> str:
    return html.escape(text or "")


def money(amount: Decimal | float) -> str:
    return f"${Decimal(str(amount)):.2f}"


def dt(value: datetime | None) -> str:
    return value.strftime("%d.%m.%Y %H:%M") if value else "—"


def date_only(value: datetime | None) -> str:
    return value.strftime("%d.%m.%Y") if value else "—"


def ram_gb(ram_mb: int) -> str:
    gb = ram_mb / 1024
    return f"{gb:.0f}" if gb == int(gb) else f"{gb:.1f}"
