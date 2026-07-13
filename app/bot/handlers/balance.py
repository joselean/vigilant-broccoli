"""Balance view and deposit flow (stub with a hook for real payment providers)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import DepositCb, deposit_amounts_kb
from app.models import Transaction, User
from app.utils.formatting import dt, money

router = Router(name="balance")

TX_TITLES = {
    "deposit": "➕ Пополнение",
    "purchase": "🛒 Покупка",
    "renewal": "📅 Продление",
    "refund": "↩️ Возврат",
    "referral_bonus": "🤝 Реф. бонус",
    "admin_adjustment": "⚙️ Корректировка",
}


@router.message(F.text == texts.MAIN_MENU_BALANCE)
async def balance_menu(message: Message, session: AsyncSession, user: User) -> None:
    result = await session.scalars(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.id.desc())
        .limit(10)
    )
    txs = list(result)
    if txs:
        lines = [
            f"{TX_TITLES.get(tx.type.value, tx.type.value)}: "
            f"<b>{'+' if tx.amount > 0 else ''}{money(tx.amount)}</b> · {dt(tx.created_at)}"
            for tx in txs
        ]
        tx_text = "\n".join(lines)
    else:
        tx_text = texts.NO_TRANSACTIONS
    await message.answer(
        texts.BALANCE_INFO.format(balance=money(user.balance), transactions=tx_text)
    )
    await message.answer(texts.DEPOSIT_CHOOSE_AMOUNT, reply_markup=deposit_amounts_kb())


@router.callback_query(DepositCb.filter())
async def deposit_stub(cb: CallbackQuery, callback_data: DepositCb) -> None:
    """Заглушка пополнения.

    Хук для интеграции платёжных систем:
    1. Создать инвойс у платёжного провайдера (CryptoBot / YooKassa / Telegram Stars).
    2. Отправить пользователю ссылку/инвойс.
    3. В webhook-обработчике платежа вызвать app.services.balance.deposit(...).
    """
    await cb.answer()
    await cb.message.edit_text(texts.DEPOSIT_STUB.format(amount=money(callback_data.amount)))
