"""Background jobs: expiration notices, status sync, auto-renewal, cleanup."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import select

from app.bot import texts
from app.core.db import get_session
from app.models import Order, OrderStatus, Server, ServerStatus, User
from app.providers import ProviderError, get_provider
from app.services.balance import InsufficientBalanceError
from app.services.servers import renew
from app.utils.formatting import date_only, money

_SYNCABLE = (
    ServerStatus.PROVISIONING,
    ServerStatus.ACTIVE,
    ServerStatus.STOPPED,
    ServerStatus.REBOOTING,
    ServerStatus.REINSTALLING,
)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    # Ежедневно в 09:00 UTC — уведомления об истечении
    scheduler.add_job(
        check_expiring_servers, CronTrigger(hour=9, minute=0), args=[bot], id="check_expiring"
    )
    # Каждые 10 минут — синхронизация статусов с провайдерами
    scheduler.add_job(
        sync_server_statuses, IntervalTrigger(minutes=10), args=[bot], id="sync_statuses"
    )
    # Ежедневно в 08:00 UTC — автопродление (до уведомлений)
    scheduler.add_job(autorenew_servers, CronTrigger(hour=8, minute=0), args=[bot], id="autorenew")
    # Ежедневно в 10:00 UTC — удаление серверов, истёкших более 2 дней назад
    scheduler.add_job(
        delete_long_expired, CronTrigger(hour=10, minute=0), args=[bot], id="delete_expired"
    )
    # Каждые 2 минуты — подхват "зависших" оплаченных заказов
    # (например, перезапущенных из веб-админки или потерянных при рестарте бота)
    scheduler.add_job(
        provision_stuck_orders, IntervalTrigger(minutes=2), args=[bot], id="provision_stuck"
    )
    return scheduler


async def provision_stuck_orders(bot: Bot) -> None:
    """Запускает provisioning для заказов в статусе PAID старше 5 минут.

    Порог нужен, чтобы не конкурировать с фоновой задачей, которую бот
    запускает сразу после оплаты.
    """
    from app.services.provisioning import provision_order

    threshold = datetime.now(UTC) - timedelta(minutes=5)
    async with get_session() as session:
        result = await session.scalars(
            select(Order.id).where(
                Order.status == OrderStatus.PAID, Order.updated_at <= threshold
            )
        )
        order_ids = list(result)
    for order_id in order_ids:
        logger.info("Picking up stuck paid order #{}", order_id)
        await provision_order(bot, order_id)


async def check_expiring_servers(bot: Bot) -> None:
    """Уведомления за 7 дней и за 1 день до истечения + пометка истёкших."""
    now = datetime.now(UTC)
    async with get_session() as session:
        result = await session.scalars(
            select(Server).where(Server.status.in_(_SYNCABLE))
        )
        for server in result:
            user = await session.get(User, server.user_id)
            if user is None:
                continue
            days_left = (server.expires_at - now).days
            if server.expires_at <= now:
                server.status = ServerStatus.EXPIRED
                continue
            if days_left < 1 and not server.notified_1d:
                server.notified_1d = True
                await _safe_send(
                    bot, user.telegram_id,
                    texts.EXPIRING_1D.format(
                        hostname=server.hostname,
                        ip=server.main_ip or "—",
                        expires=date_only(server.expires_at),
                    ),
                )
            elif days_left < 7 and not server.notified_7d:
                server.notified_7d = True
                await _safe_send(
                    bot, user.telegram_id,
                    texts.EXPIRING_7D.format(
                        hostname=server.hostname,
                        ip=server.main_ip or "—",
                        expires=date_only(server.expires_at),
                    ),
                )
    logger.info("check_expiring_servers finished")


async def sync_server_statuses(bot: Bot) -> None:
    """Подтягивает статусы и IP из API провайдеров; доставляет данные,
    если сервер стал active после затянувшегося provisioning."""
    async with get_session() as session:
        result = await session.scalars(select(Server).where(Server.status.in_(_SYNCABLE)))
        servers = list(result)

    for server_id in [s.id for s in servers]:
        try:
            async with get_session() as session:
                server = await session.get(Server, server_id)
                if server is None or server.status not in _SYNCABLE:
                    continue
                info = await get_provider(server.provider).get_server(server.external_server_id)
                was_provisioning = server.status is ServerStatus.PROVISIONING
                if info.main_ip:
                    server.main_ip = info.main_ip
                if info.status == "active":
                    server.status = ServerStatus.ACTIVE
                elif info.status == "stopped":
                    server.status = ServerStatus.STOPPED
                elif info.status == "error":
                    server.status = ServerStatus.ERROR

                # Затянувшийся provisioning завершился — отправляем данные доступа
                if was_provisioning and server.status is ServerStatus.ACTIVE and server.main_ip:
                    from app.services.provisioning import _ready_text

                    user = await session.get(User, server.user_id)
                    if user:
                        await _safe_send(bot, user.telegram_id, _ready_text(server))
        except ProviderError as exc:
            if exc.status_code == 404:
                # Сервер удалён на стороне провайдера
                async with get_session() as session:
                    server = await session.get(Server, server_id)
                    if server:
                        server.status = ServerStatus.DELETED
            else:
                logger.warning("Status sync failed for server {}: {}", server_id, exc)
    logger.debug("sync_server_statuses finished ({} servers)", len(servers))


async def autorenew_servers(bot: Bot) -> None:
    """Автопродление серверов, истекающих в ближайшие сутки."""
    now = datetime.now(UTC)
    deadline = now + timedelta(days=1)
    async with get_session() as session:
        result = await session.scalars(
            select(Server).where(
                Server.autorenew.is_(True),
                Server.status == ServerStatus.ACTIVE,
                Server.expires_at <= deadline,
                Server.expires_at > now,
            )
        )
        for server in result:
            user = await session.get(User, server.user_id)
            if user is None or user.is_banned:
                continue
            try:
                price = await renew(session, user, server, months=1)
                await _safe_send(
                    bot, user.telegram_id,
                    texts.AUTORENEW_OK.format(
                        hostname=server.hostname,
                        price=money(price),
                        expires=date_only(server.expires_at),
                    ),
                )
            except InsufficientBalanceError:
                await _safe_send(
                    bot, user.telegram_id,
                    texts.AUTORENEW_FAILED.format(
                        hostname=server.hostname, expires=date_only(server.expires_at)
                    ),
                )
    logger.info("autorenew_servers finished")


async def delete_long_expired(bot: Bot) -> None:
    """Удаляет у провайдера серверы, истёкшие более 2 дней назад (grace-период)."""
    cutoff = datetime.now(UTC) - timedelta(days=2)
    async with get_session() as session:
        result = await session.scalars(
            select(Server).where(
                Server.status == ServerStatus.EXPIRED, Server.expires_at <= cutoff
            )
        )
        for server in result:
            try:
                await get_provider(server.provider).delete_server(server.external_server_id)
            except ProviderError as exc:
                if exc.status_code != 404:
                    logger.error("Failed to delete expired server {}: {}", server.id, exc)
                    continue
            server.status = ServerStatus.DELETED
            user = await session.get(User, server.user_id)
            if user:
                await _safe_send(
                    bot, user.telegram_id,
                    f"🗑 Сервер <code>{server.hostname}</code> удалён из-за неоплаты.",
                )
            logger.info("Expired server {} deleted", server.id)


async def _safe_send(bot: Bot, telegram_id: int, text: str) -> None:
    try:
        await bot.send_message(telegram_id, text)
    except Exception as exc:
        logger.warning("Failed to send message to {}: {}", telegram_id, exc)
