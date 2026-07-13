"""Catalog browsing and the full order flow (FSM)."""
from __future__ import annotations

import asyncio
import re
from decimal import Decimal

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import (
    PROVIDER_TITLES,
    ImageCb,
    LocationCb,
    OrderConfirmCb,
    PeriodCb,
    PlanCb,
    PlanPageCb,
    ProviderCb,
    SkipSshCb,
    images_kb,
    locations_kb,
    order_confirm_kb,
    periods_kb,
    plans_kb,
    providers_kb,
    ssh_skip_kb,
)
from app.bot.states import OrderFlow
from app.core.security import looks_like_ssh_public_key
from app.models import Provider, User
from app.services import orders as order_service
from app.services.balance import InsufficientBalanceError
from app.services.catalog import (
    configured_providers,
    find_image,
    find_location,
    find_plan,
    get_catalog,
    plan_customer_price,
    plans_for_location,
)
from app.services.provisioning import provision_order
from app.utils.formatting import esc, money

router = Router(name="catalog")

HOSTNAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{1,30})[a-z0-9]$", re.IGNORECASE)


@router.message(F.text == texts.MAIN_MENU_CATALOG)
async def show_catalog(message: Message, state: FSMContext) -> None:
    await state.clear()
    providers = configured_providers()
    if not providers:
        await message.answer(texts.PROVIDER_UNAVAILABLE)
        return
    await state.set_state(OrderFlow.choosing_provider)
    await message.answer(texts.CHOOSE_PROVIDER, reply_markup=providers_kb(providers))


@router.callback_query(OrderFlow.choosing_provider, ProviderCb.filter())
async def choose_provider(cb: CallbackQuery, callback_data: ProviderCb, state: FSMContext) -> None:
    provider = Provider(callback_data.provider)
    await cb.answer()
    try:
        catalog = await get_catalog(provider)
    except Exception:
        await cb.message.edit_text(texts.PROVIDER_UNAVAILABLE)
        return
    await state.update_data(provider=provider.value)
    await state.set_state(OrderFlow.choosing_location)
    await cb.message.edit_text(
        texts.CHOOSE_LOCATION.format(provider=PROVIDER_TITLES[provider]),
        reply_markup=locations_kb(provider, catalog.locations),
    )


@router.callback_query(OrderFlow.choosing_location, LocationCb.filter())
async def choose_location(cb: CallbackQuery, callback_data: LocationCb, state: FSMContext) -> None:
    provider = Provider(callback_data.provider)
    catalog = await get_catalog(provider)
    location = find_location(catalog, callback_data.location_id)
    if location is None:
        await cb.answer(texts.ERROR_GENERIC, show_alert=True)
        return
    plans = plans_for_location(catalog, location.id)
    if not plans:
        await cb.answer("В этой локации нет доступных тарифов 😔", show_alert=True)
        return
    await state.update_data(
        location_id=location.id,
        location_name=f"{location.flag} {location.city} ({location.country})",
    )
    await state.set_state(OrderFlow.choosing_plan)
    await cb.answer()
    await cb.message.edit_text(
        texts.CHOOSE_PLAN.format(
            location=f"{location.flag} {location.city} ({location.country})"
        ),
        reply_markup=plans_kb(plans),
    )


@router.callback_query(OrderFlow.choosing_plan, PlanPageCb.filter())
async def paginate_plans(cb: CallbackQuery, callback_data: PlanPageCb, state: FSMContext) -> None:
    data = await state.get_data()
    catalog = await get_catalog(Provider(data["provider"]))
    plans = plans_for_location(catalog, data["location_id"])
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=plans_kb(plans, page=callback_data.page))


@router.callback_query(OrderFlow.choosing_plan, PlanCb.filter())
async def choose_plan(cb: CallbackQuery, callback_data: PlanCb, state: FSMContext) -> None:
    data = await state.get_data()
    catalog = await get_catalog(Provider(data["provider"]))
    plan = find_plan(catalog, callback_data.plan_id)
    if plan is None:
        await cb.answer(texts.ERROR_GENERIC, show_alert=True)
        return
    await state.update_data(
        plan_id=plan.id,
        plan_label=plan.label,
        provider_monthly_cost=str(plan.monthly_cost_usd),
    )
    await state.set_state(OrderFlow.choosing_image)
    await cb.answer()
    await cb.message.edit_text(texts.CHOOSE_IMAGE, reply_markup=images_kb(catalog.images))


@router.callback_query(OrderFlow.choosing_image, ImageCb.filter())
async def choose_image(cb: CallbackQuery, callback_data: ImageCb, state: FSMContext) -> None:
    data = await state.get_data()
    catalog = await get_catalog(Provider(data["provider"]))
    image = find_image(catalog, callback_data.image_id)
    if image is None:
        await cb.answer(texts.ERROR_GENERIC, show_alert=True)
        return
    await state.update_data(image_id=image.id, image_name=image.name)
    await state.set_state(OrderFlow.entering_hostname)
    await cb.answer()
    await cb.message.edit_text(texts.ENTER_HOSTNAME)


@router.message(OrderFlow.entering_hostname, F.text)
async def enter_hostname(message: Message, state: FSMContext) -> None:
    hostname = (message.text or "").strip().lower()
    if not HOSTNAME_RE.match(hostname):
        await message.answer(texts.INVALID_HOSTNAME)
        return
    await state.update_data(hostname=hostname)
    await state.set_state(OrderFlow.entering_ssh_key)
    await message.answer(texts.ASK_SSH_KEY, reply_markup=ssh_skip_kb())


@router.message(OrderFlow.entering_ssh_key, F.text)
async def enter_ssh_key(message: Message, state: FSMContext) -> None:
    key = (message.text or "").strip()
    if not looks_like_ssh_public_key(key):
        await message.answer(texts.INVALID_SSH_KEY, reply_markup=ssh_skip_kb())
        return
    await state.update_data(ssh_public_key=key)
    await _ask_period(message, state)


@router.callback_query(OrderFlow.entering_ssh_key, SkipSshCb.filter())
async def skip_ssh_key(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(ssh_public_key=None)
    await cb.answer("Сгенерируем надёжный пароль 🔑")
    await _ask_period(cb.message, state)


async def _ask_period(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    monthly = plan_customer_price_from_state(data)
    await state.set_state(OrderFlow.choosing_period)
    await message.answer(texts.CHOOSE_PERIOD, reply_markup=periods_kb(monthly))


def plan_customer_price_from_state(data: dict) -> Decimal:  # type: ignore[type-arg]
    from app.core.pricing import customer_monthly_price

    return customer_monthly_price(Decimal(data["provider_monthly_cost"]))


@router.callback_query(OrderFlow.choosing_period, PeriodCb.filter())
async def choose_period(
    cb: CallbackQuery, callback_data: PeriodCb, state: FSMContext, user: User
) -> None:
    from app.core.config import get_settings
    from app.core.pricing import period_price

    data = await state.get_data()
    months = callback_data.months
    monthly = plan_customer_price_from_state(data)
    total = period_price(monthly, months)
    await state.update_data(months=months, total=str(total))
    await state.set_state(OrderFlow.confirming)

    discount = get_settings().period_discounts.get(months, Decimal(0))
    discount_note = f" (скидка {discount}%)" if discount > 0 else ""
    auth = "SSH-ключ" if data.get("ssh_public_key") else "пароль root (сгенерируем)"
    text = texts.ORDER_SUMMARY.format(
        provider=PROVIDER_TITLES[Provider(data["provider"])],
        location=esc(data["location_name"]),
        plan=esc(data["plan_label"]),
        image=esc(data["image_name"]),
        hostname=esc(data["hostname"]),
        auth=auth,
        months=months,
        discount_note=discount_note,
        total=money(total),
        balance=money(user.balance),
    )
    if user.balance < total:
        text += texts.ORDER_INSUFFICIENT.format(missing=money(total - user.balance))
    await cb.answer()
    await cb.message.edit_text(text, reply_markup=order_confirm_kb())


@router.callback_query(OrderFlow.confirming, OrderConfirmCb.filter())
async def confirm_order(
    cb: CallbackQuery,
    callback_data: OrderConfirmCb,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    if callback_data.order_action == "cancel":
        await state.clear()
        await cb.answer()
        await cb.message.edit_text(texts.ORDER_CANCELLED)
        return

    data = await state.get_data()
    order = await order_service.create_order(
        session,
        user,
        provider=Provider(data["provider"]),
        region_id=data["location_id"],
        region_name=data["location_name"],
        plan_id=data["plan_id"],
        plan_label=data["plan_label"],
        image_id=data["image_id"],
        image_name=data["image_name"],
        hostname=data["hostname"],
        ssh_public_key=data.get("ssh_public_key"),
        months=data["months"],
        provider_monthly_cost=Decimal(data["provider_monthly_cost"]),
    )
    try:
        await order_service.pay_order(session, user, order)
    except InsufficientBalanceError:
        await cb.answer("Недостаточно средств на балансе 💸", show_alert=True)
        return

    await session.commit()
    await state.clear()
    await cb.answer()
    await cb.message.edit_text(texts.ORDER_PAID.format(order_id=order.id))

    # Provisioning выполняется в фоне, чтобы не блокировать обработку апдейтов
    asyncio.create_task(provision_order(bot, order.id))
    logger.info("Order #{} paid by user {}, provisioning started", order.id, user.id)
