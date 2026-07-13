"""«Мои серверы»: list, info and management actions."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import (
    ReinstallImageCb,
    RenewPeriodCb,
    ServerCb,
    delete_confirm_kb,
    reinstall_images_kb,
    renew_periods_kb,
    server_actions_kb,
    servers_list_kb,
)
from app.core.security import decrypt
from app.models import Server, User
from app.providers import ProviderError
from app.services import servers as server_service
from app.services.balance import InsufficientBalanceError
from app.services.catalog import find_image, get_catalog
from app.utils.formatting import date_only, esc, money

router = Router(name="servers")

STATUS_TITLES = {
    "provisioning": "🟡 Создаётся",
    "active": "🟢 Активен",
    "stopped": "🔴 Остановлен",
    "rebooting": "🔄 Перезагружается",
    "reinstalling": "💿 Переустановка ОС",
    "expired": "⚫️ Истёк",
    "error": "❗️ Ошибка",
}


@router.message(F.text == texts.MAIN_MENU_SERVERS)
async def my_servers(message: Message, session: AsyncSession, user: User) -> None:
    servers = await server_service.get_user_servers(session, user.id)
    if not servers:
        await message.answer(texts.NO_SERVERS)
        return
    await message.answer(
        f"🖥 <b>Ваши серверы</b> ({len(servers)}):", reply_markup=servers_list_kb(servers)
    )


def _server_info_text(server: Server) -> str:
    password_note = (
        "🔑 Доступ: root-пароль (нажмите «Сбросить пароль», чтобы получить новый)"
        if server.encrypted_password
        else "🔐 Доступ: по SSH-ключу"
    )
    return (
        f"🖥 <b>{esc(server.hostname)}</b>\n\n"
        f"Статус: <b>{STATUS_TITLES.get(server.status.value, server.status.value)}</b>\n"
        f"🌐 IP: <code>{esc(server.main_ip) or '—'}</code>\n"
        f"☁️ Провайдер: {server.provider.value.title()}\n"
        f"📍 Локация: {esc(server.region_name)}\n"
        f"⚙️ Тариф: {esc(server.plan_label)}\n"
        f"💿 ОС: {esc(server.image_name)}\n"
        f"💵 Цена: <b>{money(server.monthly_price)}/мес</b>\n"
        f"📅 Оплачен до: <b>{date_only(server.expires_at)}</b>\n"
        f"{password_note}\n\n"
        f"<code>ssh root@{esc(server.main_ip or '...')}</code>"
    )


async def _load_server(
    cb: CallbackQuery, session: AsyncSession, user: User, server_id: int
) -> Server | None:
    server = await server_service.get_user_server(session, user.id, server_id)
    if server is None:
        await cb.answer("Сервер не найден", show_alert=True)
    return server


@router.callback_query(ServerCb.filter(F.action == "info"))
async def server_info(
    cb: CallbackQuery, callback_data: ServerCb, session: AsyncSession, user: User
) -> None:
    server = await _load_server(cb, session, user, callback_data.server_id)
    if server is None:
        return
    await cb.answer()
    try:
        await cb.message.edit_text(
            _server_info_text(server), reply_markup=server_actions_kb(server.id)
        )
    except TelegramBadRequest:
        pass  # message is not modified — игнорируем


@router.callback_query(ServerCb.filter(F.action == "back"))
async def back_to_list(cb: CallbackQuery, session: AsyncSession, user: User) -> None:
    servers = await server_service.get_user_servers(session, user.id)
    await cb.answer()
    if not servers:
        await cb.message.edit_text(texts.NO_SERVERS)
        return
    await cb.message.edit_text(
        f"🖥 <b>Ваши серверы</b> ({len(servers)}):", reply_markup=servers_list_kb(servers)
    )


@router.callback_query(ServerCb.filter(F.action == "reboot"))
async def server_reboot(
    cb: CallbackQuery, callback_data: ServerCb, session: AsyncSession, user: User
) -> None:
    server = await _load_server(cb, session, user, callback_data.server_id)
    if server is None:
        return
    try:
        await server_service.reboot(server)
    except ProviderError as exc:
        logger.error("Reboot failed for server {}: {}", server.id, exc)
        await cb.answer(texts.ERROR_GENERIC, show_alert=True)
        return
    await cb.answer("🔄 Перезагрузка запущена!", show_alert=True)


@router.callback_query(ServerCb.filter(F.action == "reinstall"))
async def server_reinstall_menu(
    cb: CallbackQuery, callback_data: ServerCb, session: AsyncSession, user: User
) -> None:
    server = await _load_server(cb, session, user, callback_data.server_id)
    if server is None:
        return
    try:
        catalog = await get_catalog(server.provider)
    except Exception:
        await cb.answer(texts.PROVIDER_UNAVAILABLE, show_alert=True)
        return
    await cb.answer()
    await cb.message.edit_text(
        "💿 <b>Переустановка ОС</b>\n\n"
        "⚠️ <b>Все данные на сервере будут удалены!</b>\n"
        "Выберите новую операционную систему:",
        reply_markup=reinstall_images_kb(server.id, catalog.images),
    )


@router.callback_query(ReinstallImageCb.filter())
async def server_reinstall(
    cb: CallbackQuery, callback_data: ReinstallImageCb, session: AsyncSession, user: User
) -> None:
    server = await _load_server(cb, session, user, callback_data.server_id)
    if server is None:
        return
    catalog = await get_catalog(server.provider)
    image = find_image(catalog, callback_data.image_id)
    if image is None:
        await cb.answer(texts.ERROR_GENERIC, show_alert=True)
        return
    try:
        await server_service.reinstall(server, image.id, image.name)
    except ProviderError as exc:
        logger.error("Reinstall failed for server {}: {}", server.id, exc)
        await cb.answer(texts.ERROR_GENERIC, show_alert=True)
        return
    await cb.answer()
    await cb.message.edit_text(
        f"💿 Переустановка <b>{esc(image.name)}</b> запущена!\n"
        "Обычно занимает несколько минут. Данные для доступа остаются прежними "
        "(SSH-ключ или пароль)."
    )


@router.callback_query(ServerCb.filter(F.action == "resetpw"))
async def server_reset_password(
    cb: CallbackQuery, callback_data: ServerCb, session: AsyncSession, user: User
) -> None:
    server = await _load_server(cb, session, user, callback_data.server_id)
    if server is None:
        return
    try:
        new_password = await server_service.reset_password(server)
    except ProviderError as exc:
        logger.error("Password reset failed for server {}: {}", server.id, exc)
        await cb.answer(texts.ERROR_GENERIC, show_alert=True)
        return
    if new_password is None:
        await cb.answer(
            "К сожалению, Vultr не поддерживает сброс пароля через API. "
            "Используйте консоль восстановления или переустановку ОС.",
            show_alert=True,
        )
        return
    await cb.answer()
    await cb.message.answer(
        "🔑 <b>Новый root-пароль:</b>\n"
        f"<code>{esc(new_password)}</code>\n\n"
        "⚠️ Сохраните его в надёжном месте. Сервер может перезагрузиться."
    )


@router.callback_query(ServerCb.filter(F.action == "renew"))
async def server_renew_menu(
    cb: CallbackQuery, callback_data: ServerCb, session: AsyncSession, user: User
) -> None:
    server = await _load_server(cb, session, user, callback_data.server_id)
    if server is None:
        return
    await cb.answer()
    await cb.message.edit_text(
        f"📅 <b>Продление сервера</b> <code>{esc(server.hostname)}</code>\n"
        f"Оплачен до: <b>{date_only(server.expires_at)}</b>\n"
        f"Ваш баланс: <b>{money(user.balance)}</b>\n\n"
        "Выберите период:",
        reply_markup=renew_periods_kb(server),
    )


@router.callback_query(RenewPeriodCb.filter())
async def server_renew(
    cb: CallbackQuery, callback_data: RenewPeriodCb, session: AsyncSession, user: User
) -> None:
    server = await _load_server(cb, session, user, callback_data.server_id)
    if server is None:
        return
    try:
        price = await server_service.renew(session, user, server, callback_data.months)
    except InsufficientBalanceError:
        await cb.answer(
            "Недостаточно средств. Пополните баланс в разделе «💰 Баланс».", show_alert=True
        )
        return
    await cb.answer()
    await cb.message.edit_text(
        f"✅ Сервер <code>{esc(server.hostname)}</code> продлён на "
        f"<b>{callback_data.months} мес.</b>\n"
        f"Списано: <b>{money(price)}</b>. Оплачен до: <b>{date_only(server.expires_at)}</b>."
    )


@router.callback_query(ServerCb.filter(F.action == "delete"))
async def server_delete_confirm(
    cb: CallbackQuery, callback_data: ServerCb, session: AsyncSession, user: User
) -> None:
    server = await _load_server(cb, session, user, callback_data.server_id)
    if server is None:
        return
    await cb.answer()
    await cb.message.edit_text(
        f"🗑 <b>Удаление сервера</b> <code>{esc(server.hostname)}</code>\n\n"
        "⚠️ <b>Внимание!</b> Сервер и все данные будут удалены безвозвратно.\n"
        "Средства за оставшийся период не возвращаются.\n\n"
        "Вы уверены?",
        reply_markup=delete_confirm_kb(server.id),
    )


@router.callback_query(ServerCb.filter(F.action == "delconfirm"))
async def server_delete(
    cb: CallbackQuery, callback_data: ServerCb, session: AsyncSession, user: User
) -> None:
    server = await _load_server(cb, session, user, callback_data.server_id)
    if server is None:
        return
    try:
        await server_service.delete(session, server)
    except ProviderError as exc:
        logger.error("Delete failed for server {}: {}", server.id, exc)
        await cb.answer(texts.ERROR_GENERIC, show_alert=True)
        return
    await cb.answer()
    await cb.message.edit_text(f"🗑 Сервер <code>{esc(server.hostname)}</code> удалён.")
