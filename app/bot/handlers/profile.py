"""Profile and referral program."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.core.config import get_settings
from app.models import User
from app.services.servers import get_user_servers
from app.services.users import count_referrals
from app.utils.formatting import date_only, money

router = Router(name="profile")


@router.message(F.text == texts.MAIN_MENU_PROFILE)
async def profile(message: Message, session: AsyncSession, user: User) -> None:
    bot_info = await message.bot.get_me()
    servers = await get_user_servers(session, user.id)
    referrals = await count_referrals(session, user.id)
    await message.answer(
        texts.PROFILE.format(
            telegram_id=user.telegram_id,
            registered=date_only(user.created_at),
            balance=money(user.balance),
            servers=len(servers),
            autorenew="включено ✅" if user.autorenew_enabled else "выключено ❌",
            bonus_percent=get_settings().referral_bonus_percent,
            referrals=referrals,
            ref_link=f"https://t.me/{bot_info.username}?start=ref{user.telegram_id}",
        )
    )


@router.message(F.text == "/autorenew")
async def toggle_autorenew(message: Message, user: User) -> None:
    """Переключить автопродление (применяется к новым серверам и списаниям)."""
    user.autorenew_enabled = not user.autorenew_enabled
    status = "включено ✅" if user.autorenew_enabled else "выключено ❌"
    await message.answer(
        f"🔄 Автопродление {status}\n\n"
        "При включённом автопродлении серверы продлеваются автоматически "
        "за 1 день до истечения, если на балансе достаточно средств."
    )
