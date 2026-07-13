"""Simple in-memory rate limiting (anti-spam)."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.bot import texts

WINDOW_SECONDS = 3.0
MAX_EVENTS_PER_WINDOW = 5


class ThrottlingMiddleware(BaseMiddleware):
    """Не более N событий за окно; лишнее молча отбрасываем с предупреждением."""

    def __init__(self) -> None:
        self._events: dict[int, deque[float]] = defaultdict(deque)
        self._warned_at: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        now = time.monotonic()
        q = self._events[tg_user.id]
        while q and now - q[0] > WINDOW_SECONDS:
            q.popleft()
        q.append(now)

        if len(q) > MAX_EVENTS_PER_WINDOW:
            # предупреждаем не чаще раза в 10 секунд
            if now - self._warned_at.get(tg_user.id, 0) > 10:
                self._warned_at[tg_user.id] = now
                if isinstance(event, Message):
                    await event.answer(texts.THROTTLED)
                elif isinstance(event, CallbackQuery):
                    await event.answer(texts.THROTTLED, show_alert=False)
            return None

        return await handler(event, data)
