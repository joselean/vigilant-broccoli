"""User registration and profile operations."""
from __future__ import annotations

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str,
    referrer_telegram_id: int | None = None,
) -> tuple[User, bool]:
    """Returns (user, created)."""
    user = await get_by_telegram_id(session, telegram_id)
    if user:
        user.username = username
        user.full_name = full_name
        user.last_seen_at = datetime.now(UTC)
        return user, False

    referrer_id: int | None = None
    if referrer_telegram_id and referrer_telegram_id != telegram_id:
        referrer = await get_by_telegram_id(session, referrer_telegram_id)
        if referrer:
            referrer_id = referrer.id

    user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        referrer_id=referrer_id,
        last_seen_at=datetime.now(UTC),
    )
    session.add(user)
    await session.flush()
    logger.info("New user registered: tg={} referrer_id={}", telegram_id, referrer_id)
    return user, True


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def count_referrals(session: AsyncSession, user_id: int) -> int:
    result = await session.scalar(
        select(func.count()).select_from(User).where(User.referrer_id == user_id)
    )
    return result or 0
