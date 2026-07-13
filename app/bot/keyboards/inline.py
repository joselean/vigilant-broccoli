"""Inline keyboards and callback data factories."""
from __future__ import annotations

from decimal import Decimal

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.config import get_settings
from app.core.pricing import available_periods, period_price
from app.models import Provider, Server
from app.providers import Image, Location, Plan
from app.services.catalog import plan_customer_price
from app.utils.formatting import money

PROVIDER_TITLES = {Provider.VULTR: "Vultr", Provider.HETZNER: "Hetzner"}


# --- Callback data ----------------------------------------------------------

class ProviderCb(CallbackData, prefix="prov"):
    provider: str


class LocationCb(CallbackData, prefix="loc"):
    provider: str
    location_id: str


class PlanPageCb(CallbackData, prefix="planpg"):
    page: int


class PlanCb(CallbackData, prefix="plan"):
    plan_id: str


class ImageCb(CallbackData, prefix="img"):
    image_id: str


class SkipSshCb(CallbackData, prefix="skipssh"):
    pass


class PeriodCb(CallbackData, prefix="period"):
    months: int


class OrderConfirmCb(CallbackData, prefix="ordconf"):
    order_action: str  # confirm | cancel


class ServerCb(CallbackData, prefix="srv"):
    server_id: int
    action: str  # info | reboot | reinstall | resetpw | renew | delete | delconfirm | back


class ReinstallImageCb(CallbackData, prefix="reimg"):
    server_id: int
    image_id: str


class RenewPeriodCb(CallbackData, prefix="renew"):
    server_id: int
    months: int


class DepositCb(CallbackData, prefix="dep"):
    amount: int


# --- Keyboards ---------------------------------------------------------------

def providers_kb(providers: list[Provider]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in providers:
        b.button(text=f"☁️ {PROVIDER_TITLES[p]}", callback_data=ProviderCb(provider=p.value))
    b.adjust(1)
    return b.as_markup()


def locations_kb(provider: Provider, locations: list[Location]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for loc in sorted(locations, key=lambda x: (x.country, x.city)):
        b.button(
            text=f"{loc.flag} {loc.city} ({loc.country})",
            callback_data=LocationCb(provider=provider.value, location_id=loc.id),
        )
    b.adjust(2)
    return b.as_markup()


PLANS_PER_PAGE = 8


def plans_kb(plans: list[Plan], page: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    start = page * PLANS_PER_PAGE
    for plan in plans[start:start + PLANS_PER_PAGE]:
        price = plan_customer_price(plan)
        b.button(
            text=f"{plan.label} — {money(price)}/мес",
            callback_data=PlanCb(plan_id=plan.id),
        )
    b.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=PlanPageCb(page=page - 1).pack())
        )
    if start + PLANS_PER_PAGE < len(plans):
        nav.append(
            InlineKeyboardButton(text="Ещё ➡️", callback_data=PlanPageCb(page=page + 1).pack())
        )
    if nav:
        b.row(*nav)
    return b.as_markup()


def images_kb(images: list[Image]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for img in images:
        b.button(text=f"💿 {img.name}", callback_data=ImageCb(image_id=img.id))
    b.adjust(2)
    return b.as_markup()


def ssh_skip_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔑 Использовать пароль", callback_data=SkipSshCb())
    return b.as_markup()


def periods_kb(monthly_price: Decimal) -> InlineKeyboardMarkup:
    discounts = get_settings().period_discounts
    b = InlineKeyboardBuilder()
    for months in available_periods():
        total = period_price(monthly_price, months)
        discount = discounts.get(months, Decimal(0))
        label = f"{months} мес. — {money(total)}"
        if discount > 0:
            label += f" (-{discount}%)"
        b.button(text=label, callback_data=PeriodCb(months=months))
    b.adjust(1)
    return b.as_markup()


def order_confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Оплатить и создать", callback_data=OrderConfirmCb(order_action="confirm"))
    b.button(text="❌ Отменить", callback_data=OrderConfirmCb(order_action="cancel"))
    b.adjust(1)
    return b.as_markup()


def servers_list_kb(servers: list[Server]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in servers:
        status_emoji = {"active": "🟢", "stopped": "🔴", "expired": "⚫️"}.get(s.status.value, "🟡")
        b.button(
            text=f"{status_emoji} {s.hostname} · {s.main_ip or '...'}",
            callback_data=ServerCb(server_id=s.id, action="info"),
        )
    b.adjust(1)
    return b.as_markup()


def server_actions_kb(server_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔄 Перезагрузить", callback_data=ServerCb(server_id=server_id, action="reboot"))
    b.button(text="💿 Переустановить ОС", callback_data=ServerCb(server_id=server_id, action="reinstall"))
    b.button(text="🔑 Сбросить пароль", callback_data=ServerCb(server_id=server_id, action="resetpw"))
    b.button(text="📅 Продлить", callback_data=ServerCb(server_id=server_id, action="renew"))
    b.button(text="🗑 Удалить", callback_data=ServerCb(server_id=server_id, action="delete"))
    b.button(text="⬅️ К списку", callback_data=ServerCb(server_id=server_id, action="back"))
    b.adjust(2, 2, 2)
    return b.as_markup()


def reinstall_images_kb(server_id: int, images: list[Image]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for img in images:
        b.button(
            text=f"💿 {img.name}",
            callback_data=ReinstallImageCb(server_id=server_id, image_id=img.id),
        )
    b.button(text="⬅️ Назад", callback_data=ServerCb(server_id=server_id, action="info"))
    b.adjust(2)
    return b.as_markup()


def renew_periods_kb(server: Server) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for months in available_periods():
        total = period_price(server.monthly_price, months)
        b.button(
            text=f"{months} мес. — {money(total)}",
            callback_data=RenewPeriodCb(server_id=server.id, months=months),
        )
    b.button(text="⬅️ Назад", callback_data=ServerCb(server_id=server.id, action="info"))
    b.adjust(1)
    return b.as_markup()


def delete_confirm_kb(server_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(
        text="🗑 Да, удалить безвозвратно",
        callback_data=ServerCb(server_id=server_id, action="delconfirm"),
    )
    b.button(text="⬅️ Отмена", callback_data=ServerCb(server_id=server_id, action="info"))
    b.adjust(1)
    return b.as_markup()


def deposit_amounts_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for amount in (5, 10, 25, 50, 100):
        b.button(text=f"💵 ${amount}", callback_data=DepositCb(amount=amount))
    b.adjust(3)
    return b.as_markup()
