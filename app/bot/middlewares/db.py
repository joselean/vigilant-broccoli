"""Provides an AsyncSession per update and registers/loads the user."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from app.bot import texts
from app.core.db import session_factory
from app.services.users import get_or_create_user


class DbUserMiddleware(BaseMiddleware):
    """Открывает сессию БД, подгружает/регистрирует пользователя, отсекает забаненных."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        async with session_factory() as session:
            user, created = await get_or_create_user(
                session,
                telegram_id=tg_user.id,
                username=tg_user.username,
                full_name=tg_user.full_name,
            )
            await session.commit()

            if user.is_banned:
                await self._reply(event, texts.BANNED)
                return None

            data["session"] = session
            data["user"] = user
            data["user_created"] = created
            result = await handler(event, data)
            await session.commit()
            return result

    @staticmethod
    async def _reply(event: TelegramObject, text: str) -> None:
        if isinstance(event, Update):
            if event.message:
                await event.message.answer(text)
            elif event.callback_query:
                await event.callback_query.answer(text, show_alert=True)
        elif isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
