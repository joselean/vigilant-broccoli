"""Admin commands in Telegram: quick management without the web panel.

/admin — сводка и список команд
/find <id|@username> — карточка пользователя
/addbalance <telegram_id> <amount> — изменить баланс (+/-)
/ban <telegram_id> | /unban <telegram_id>
/reply <ticket_id> <text> — ответ на обращение
/orders — последние заказы
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import (
    Order,
    Server,
    ServerStatus,
    SupportTicket,
    TicketStatus,
    Transaction,
    TransactionType,
    User,
)
from app.services.balance import apply_transaction
from app.utils.formatting import dt, esc, money

router = Router(name="admin")
router.message.filter(F.from_user.id.in_(get_settings().admin_ids))


@router.message(Command("admin"))
async def admin_panel(message: Message, session: AsyncSession) -> None:
    users_count = await session.scalar(select(func.count()).select_from(User)) or 0
    active_servers = await session.scalar(
        select(func.count()).select_from(Server).where(Server.status == ServerStatus.ACTIVE)
    ) or 0
    revenue = await session.scalar(
        select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
            Transaction.type.in_([TransactionType.PURCHASE, TransactionType.RENEWAL])
        )
    ) or Decimal(0)
    open_tickets = await session.scalar(
        select(func.count()).select_from(SupportTicket).where(
            SupportTicket.status == TicketStatus.OPEN
        )
    ) or 0
    await message.answer(
        "⚙️ <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{users_count}</b>\n"
        f"🖥 Активных серверов: <b>{active_servers}</b>\n"
        f"💰 Выручка (всего): <b>{money(revenue)}</b>\n"
        f"🆘 Открытых тикетов: <b>{open_tickets}</b>\n\n"
        "<b>Команды:</b>\n"
        "<code>/find id|@username</code> — найти пользователя\n"
        "<code>/addbalance tg_id сумма</code> — изменить баланс\n"
        "<code>/ban tg_id</code> / <code>/unban tg_id</code>\n"
        "<code>/reply ticket_id текст</code> — ответить на тикет\n"
        "<code>/orders</code> — последние заказы"
    )


@router.message(Command("find"))
async def find_user(message: Message, command: CommandObject, session: AsyncSession) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("Использование: <code>/find 123456789</code> или <code>/find @username</code>")
        return
    if query.startswith("@"):
        target = await session.scalar(select(User).where(User.username == query[1:]))
    elif query.isdigit():
        target = await session.scalar(select(User).where(User.telegram_id == int(query)))
    else:
        target = None
    if target is None:
        await message.answer("Пользователь не найден.")
        return
    servers_count = await session.scalar(
        select(func.count()).select_from(Server).where(
            Server.user_id == target.id, Server.status != ServerStatus.DELETED
        )
    ) or 0
    await message.answer(
        f"👤 <b>{esc(target.full_name)}</b> (@{esc(target.username or '—')})\n"
        f"TG ID: <code>{target.telegram_id}</code>\n"
        f"Баланс: <b>{money(target.balance)}</b>\n"
        f"Серверов: {servers_count}\n"
        f"Забанен: {'да 🚫' if target.is_banned else 'нет'}\n"
        f"Регистрация: {dt(target.created_at)}"
    )


@router.message(Command("addbalance"))
async def add_balance(message: Message, command: CommandObject, session: AsyncSession) -> None:
    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.answer("Использование: <code>/addbalance 123456789 10.50</code>")
        return
    try:
        tg_id, amount = int(parts[0]), Decimal(parts[1])
    except (ValueError, InvalidOperation):
        await message.answer("Неверный формат аргументов.")
        return
    target = await session.scalar(select(User).where(User.telegram_id == tg_id))
    if target is None:
        await message.answer("Пользователь не найден.")
        return
    await apply_transaction(
        session, target, amount, TransactionType.ADMIN_ADJUSTMENT,
        f"Корректировка администратором (tg={message.from_user.id})",
    )
    logger.info("Admin {} changed balance of {} by {}", message.from_user.id, tg_id, amount)
    await message.answer(
        f"✅ Баланс пользователя <code>{tg_id}</code> изменён на {money(amount)}. "
        f"Текущий баланс: <b>{money(target.balance)}</b>"
    )


@router.message(Command("ban"))
async def ban_user(message: Message, command: CommandObject, session: AsyncSession) -> None:
    await _set_ban(message, command, session, banned=True)


@router.message(Command("unban"))
async def unban_user(message: Message, command: CommandObject, session: AsyncSession) -> None:
    await _set_ban(message, command, session, banned=False)


async def _set_ban(
    message: Message, command: CommandObject, session: AsyncSession, banned: bool
) -> None:
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Использование: <code>/ban 123456789</code>")
        return
    target = await session.scalar(select(User).where(User.telegram_id == int(arg)))
    if target is None:
        await message.answer("Пользователь не найден.")
        return
    target.is_banned = banned
    await message.answer(f"{'🚫 Забанен' if banned else '✅ Разбанен'}: <code>{arg}</code>")


@router.message(Command("reply"))
async def reply_ticket(
    message: Message, command: CommandObject, session: AsyncSession, bot: Bot
) -> None:
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[0].isdigit():
        await message.answer("Использование: <code>/reply 42 текст ответа</code>")
        return
    ticket = await session.get(SupportTicket, int(parts[0]))
    if ticket is None:
        await message.answer("Тикет не найден.")
        return
    ticket.answer = parts[1]
    ticket.status = TicketStatus.ANSWERED
    target = await session.get(User, ticket.user_id)
    if target:
        try:
            await bot.send_message(
                target.telegram_id,
                f"💬 <b>Ответ поддержки на обращение #{ticket.id}:</b>\n\n{esc(parts[1])}",
            )
            await message.answer("✅ Ответ отправлен.")
        except Exception as exc:
            await message.answer(f"⚠️ Не удалось доставить ответ: {esc(str(exc))}")


@router.message(Command("orders"))
async def last_orders(message: Message, session: AsyncSession) -> None:
    result = await session.scalars(select(Order).order_by(Order.id.desc()).limit(10))
    orders = list(result)
    if not orders:
        await message.answer("Заказов пока нет.")
        return
    lines = [
        f"#{o.id} · {o.status.value} · {o.provider.value} · {esc(o.plan_label)} · "
        f"{money(o.total_price)} · {dt(o.created_at)}"
        for o in orders
    ]
    await message.answer("🧾 <b>Последние заказы:</b>\n\n" + "\n".join(lines))
