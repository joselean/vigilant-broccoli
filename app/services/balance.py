"""Balance and transaction ledger. Все изменения баланса — только через эти функции."""
from __future__ import annotations

from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, TransactionType, User


class InsufficientBalanceError(Exception):
    pass


async def apply_transaction(
    session: AsyncSession,
    user: User,
    amount: Decimal,
    tx_type: TransactionType,
    description: str = "",
    external_payment_id: str | None = None,
) -> Transaction:
    """Atomically change user balance and write a ledger record.

    amount > 0 — зачисление, amount < 0 — списание.
    """
    new_balance = user.balance + amount
    if new_balance < 0:
        raise InsufficientBalanceError(
            f"User {user.id}: balance {user.balance} + {amount} < 0"
        )
    user.balance = new_balance
    tx = Transaction(
        user_id=user.id,
        type=tx_type,
        amount=amount,
        balance_after=new_balance,
        description=description,
        external_payment_id=external_payment_id,
    )
    session.add(tx)
    await session.flush()
    logger.info(
        "Transaction: user={} type={} amount={} balance_after={}",
        user.id, tx_type.value, amount, new_balance,
    )
    return tx


async def deposit(
    session: AsyncSession,
    user: User,
    amount: Decimal,
    description: str = "Пополнение баланса",
    external_payment_id: str | None = None,
) -> Transaction:
    """Хук для платёжных систем: CryptoBot / YooKassa / Telegram Stars.

    Платёжный провайдер после подтверждения оплаты должен вызвать эту функцию.
    """
    return await apply_transaction(
        session, user, amount, TransactionType.DEPOSIT, description, external_payment_id
    )
