"""/start: registration, referral deep-link, main menu."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.reply import main_menu
from app.models import User
from app.services.users import get_by_telegram_id

router = Router(name="start")


@router.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
    user_created: bool,
) -> None:
    # Реферальная ссылка вида https://t.me/<bot>?start=ref<telegram_id>
    payload = command.args or ""
    if user_created and payload.startswith("ref") and payload[3:].isdigit():
        referrer = await get_by_telegram_id(session, int(payload[3:]))
        if referrer and referrer.id != user.id:
            user.referrer_id = referrer.id
    await _greet(message, user, user_created)


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, user_created: bool) -> None:
    await _greet(message, user, user_created)


async def _greet(message: Message, user: User, created: bool) -> None:
    bot_info = await message.bot.get_me()
    if created:
        text = texts.WELCOME.format(bot_name=bot_info.full_name)
    else:
        text = texts.WELCOME_BACK.format(name=user.full_name or "друг")
    await message.answer(text, reply_markup=main_menu())
