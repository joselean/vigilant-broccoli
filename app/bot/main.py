"""Bot entrypoint: polling + scheduler in one process.

Запуск: python -m app.bot.main
"""
from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from app.bot.handlers import setup_routers
from app.bot.middlewares.db import DbUserMiddleware
from app.bot.middlewares.throttling import ThrottlingMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.scheduler.jobs import setup_scheduler


async def main() -> None:
    setup_logging("bot")
    settings = get_settings()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Порядок важен: сначала rate-limit, потом БД/пользователь
    dp.update.outer_middleware(ThrottlingMiddleware())
    dp.update.outer_middleware(DbUserMiddleware())

    dp.include_router(setup_routers())

    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Scheduler started")

    logger.info("Bot starting (polling)...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
