"""Server provisioning: create at provider, poll until active, deliver credentials."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from loguru import logger

from app.core.pricing import customer_monthly_price
from app.core.security import decrypt, encrypt, generate_password
from app.core.db import get_session
from app.models import Order, OrderStatus, Server, ServerStatus, User
from app.providers import ProviderError, get_provider
from app.services.orders import refund_order
from app.utils.cloud_init import build_user_data
from app.utils.formatting import esc, money

POLL_INTERVAL_SECONDS = 15
POLL_MAX_ATTEMPTS = 60  # ~15 минут


async def provision_order(bot: Bot, order_id: int) -> None:
    """Full provisioning flow for a paid order. Runs as a background asyncio task.

    Ошибка на любом шаге -> возврат средств и уведомление клиента.
    """
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order is None or order.status is not OrderStatus.PAID:
            logger.warning("provision_order: order {} not found or not paid", order_id)
            return
        user = await session.get(User, order.user_id)
        assert user is not None
        telegram_id = user.telegram_id

        order.status = OrderStatus.PROVISIONING

        root_password = None if order.ssh_public_key else generate_password()
        user_data = build_user_data(
            hostname=order.hostname,
            ssh_public_key=order.ssh_public_key,
            root_password=root_password,
        )

        client = get_provider(order.provider)
        try:
            info = await client.create_server(
                hostname=order.hostname,
                region_id=order.region_id,
                plan_id=order.plan_id,
                image_id=order.image_id,
                user_data=user_data,
                ssh_public_key=order.ssh_public_key,
                root_password=root_password,
            )
        except ProviderError as exc:
            logger.error("Provisioning failed for order #{}: {}", order.id, exc)
            await refund_order(session, order, str(exc))
            await _notify(bot, telegram_id, _failed_text(order))
            return

        server = Server(
            user_id=order.user_id,
            order_id=order.id,
            provider=order.provider,
            external_server_id=info.external_id,
            status=ServerStatus.PROVISIONING,
            hostname=order.hostname,
            main_ip=info.main_ip,
            region_id=order.region_id,
            region_name=order.region_name,
            plan_id=order.plan_id,
            plan_label=order.plan_label,
            image_name=order.image_name,
            encrypted_password=encrypt(root_password) if root_password else None,
            ssh_public_key=order.ssh_public_key,
            monthly_price=customer_monthly_price(order.provider_monthly_cost),
            provider_monthly_cost=order.provider_monthly_cost,
            expires_at=datetime.now(UTC) + timedelta(days=30 * order.months),
            autorenew=user.autorenew_enabled,
        )
        session.add(server)
        await session.flush()
        server_id = server.id

    # Poll status outside of the DB transaction
    active_info = None
    for attempt in range(POLL_MAX_ATTEMPTS):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        try:
            async with get_session() as session:
                server = await session.get(Server, server_id)
                if server is None:
                    return
                info = await get_provider(server.provider).get_server(server.external_server_id)
                if info.main_ip:
                    server.main_ip = info.main_ip
                if info.status == "active" and info.main_ip:
                    server.status = ServerStatus.ACTIVE
                    order = await session.get(Order, server.order_id)
                    if order:
                        order.status = OrderStatus.COMPLETED
                    active_info = info
                    break
                if info.status == "error":
                    logger.error("Server {} entered error state", server_id)
                    break
        except ProviderError as exc:
            logger.warning("Polling attempt {} failed for server {}: {}", attempt, server_id, exc)

    if active_info is None:
        # Не дождались active — оставляем provisioning, планировщик досинхронизирует
        await _notify(
            bot,
            telegram_id,
            "⏳ Сервер создаётся дольше обычного. Мы пришлём данные, как только он будет готов.",
        )
        return

    async with get_session() as session:
        server = await session.get(Server, server_id)
        assert server is not None
        await _notify(bot, telegram_id, _ready_text(server))
        logger.info("Server {} provisioned and delivered to tg={}", server_id, telegram_id)


def _ready_text(server: Server) -> str:
    password_line = ""
    if server.encrypted_password:
        password_line = f"\n🔑 <b>Пароль root:</b> <code>{esc(decrypt(server.encrypted_password))}</code>"
    auth_hint = (
        "по вашему SSH-ключу" if server.ssh_public_key else "по паролю выше"
    )
    return (
        "🎉 <b>Ваш сервер готов!</b>\n\n"
        f"🖥 <b>Hostname:</b> <code>{esc(server.hostname)}</code>\n"
        f"🌐 <b>IP-адрес:</b> <code>{esc(server.main_ip)}</code>\n"
        f"📍 <b>Локация:</b> {esc(server.region_name)}\n"
        f"⚙️ <b>Тариф:</b> {esc(server.plan_label)}\n"
        f"💿 <b>ОС:</b> {esc(server.image_name)}"
        f"{password_line}\n\n"
        "📖 <b>Как подключиться:</b>\n"
        f"<code>ssh root@{esc(server.main_ip)}</code>\n"
        f"Авторизация {auth_hint}.\n\n"
        "На сервере уже установлены и настроены: ufw (открыт только SSH), fail2ban, htop.\n"
        "⚠️ Сохраните эти данные в надёжном месте."
    )


def _failed_text(order: Order) -> str:
    return (
        "😔 <b>Не удалось создать сервер</b>\n\n"
        f"Заказ #{order.id} отменён, средства <b>{money(order.total_price)}</b> "
        "возвращены на ваш баланс.\n"
        "Попробуйте другую локацию или тариф, либо обратитесь в поддержку."
    )


async def _notify(bot: Bot, telegram_id: int, text: str) -> None:
    try:
        await bot.send_message(telegram_id, text)
    except Exception as exc:
        logger.error("Failed to notify tg={}: {}", telegram_id, exc)
