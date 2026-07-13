"""Support tickets: user writes a message, admins get notified."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.states import SupportFlow
from app.core.config import get_settings
from app.models import SupportTicket, User
from app.utils.formatting import esc

router = Router(name="support")


@router.message(F.text == texts.MAIN_MENU_SUPPORT)
async def support_start(message: Message, state: FSMContext) -> None:
    await state.set_state(SupportFlow.writing_message)
    await message.answer(texts.SUPPORT_PROMPT)


@router.message(SupportFlow.writing_message, F.text)
async def support_message(
    message: Message, state: FSMContext, session: AsyncSession, user: User, bot: Bot
) -> None:
    ticket = SupportTicket(user_id=user.id, message=message.text or "")
    session.add(ticket)
    await session.flush()
    await state.clear()
    await message.answer(texts.SUPPORT_SENT.format(ticket_id=ticket.id))

    # Уведомляем админов о новом обращении
    admin_text = (
        f"🆘 <b>Новое обращение #{ticket.id}</b>\n"
        f"От: {esc(user.full_name)} (@{esc(user.username or '—')}, "
        f"<code>{user.telegram_id}</code>)\n\n"
        f"{esc(message.text)}\n\n"
        f"Ответить: <code>/reply {ticket.id} текст ответа</code>"
    )
    for admin_id in get_settings().admin_ids:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception as exc:
            logger.warning("Failed to notify admin {}: {}", admin_id, exc)
