"""Server management actions available to the customer."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pricing import period_price
from app.core.security import encrypt
from app.models import Server, ServerStatus, TransactionType, User
from app.providers import ProviderError, get_provider
from app.services.balance import apply_transaction


async def get_user_servers(session: AsyncSession, user_id: int) -> list[Server]:
    result = await session.scalars(
        select(Server)
        .where(Server.user_id == user_id, Server.status != ServerStatus.DELETED)
        .order_by(Server.id.desc())
    )
    return list(result)


async def get_user_server(session: AsyncSession, user_id: int, server_id: int) -> Server | None:
    server = await session.get(Server, server_id)
    if server is None or server.user_id != user_id or server.status is ServerStatus.DELETED:
        return None
    return server


async def reboot(server: Server) -> None:
    await get_provider(server.provider).reboot_server(server.external_server_id)
    logger.info("Server {} reboot requested", server.id)


async def reinstall(server: Server, image_id: str, image_name: str) -> None:
    await get_provider(server.provider).reinstall_server(server.external_server_id, image_id)
    server.image_name = image_name
    server.status = ServerStatus.REINSTALLING
    logger.info("Server {} reinstall to {} requested", server.id, image_name)


async def reset_password(server: Server) -> str | None:
    """Returns the new password (Hetzner) or None if unsupported (Vultr)."""
    new_password = await get_provider(server.provider).reset_password(server.external_server_id)
    if new_password:
        server.encrypted_password = encrypt(new_password)
        logger.info("Server {} password reset", server.id)
    return new_password


async def delete(session: AsyncSession, server: Server) -> None:
    try:
        await get_provider(server.provider).delete_server(server.external_server_id)
    except ProviderError as exc:
        # 404 = сервер уже удалён у провайдера, это не ошибка
        if exc.status_code != 404:
            raise
    server.status = ServerStatus.DELETED
    logger.info("Server {} deleted", server.id)


def renewal_price(server: Server, months: int) -> Decimal:
    return period_price(server.monthly_price, months)


async def renew(
    session: AsyncSession, user: User, server: Server, months: int
) -> Decimal:
    """Charge balance and extend expiration. Raises InsufficientBalanceError."""
    price = renewal_price(server, months)
    await apply_transaction(
        session,
        user,
        -price,
        TransactionType.RENEWAL,
        f"Продление сервера {server.hostname} на {months} мес.",
    )
    server.expires_at = server.expires_at + timedelta(days=30 * months)
    server.notified_7d = False
    server.notified_1d = False
    if server.status is ServerStatus.EXPIRED:
        server.status = ServerStatus.ACTIVE
    logger.info("Server {} renewed for {} months ({})", server.id, months, price)
    return price
