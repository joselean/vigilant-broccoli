"""Order lifecycle: creation, payment, refunds, referral bonus."""
from __future__ import annotations

from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.pricing import customer_monthly_price, period_price
from app.models import Order, OrderStatus, Provider, TransactionType, User
from app.services.balance import InsufficientBalanceError, apply_transaction


async def create_order(
    session: AsyncSession,
    user: User,
    *,
    provider: Provider,
    region_id: str,
    region_name: str,
    plan_id: str,
    plan_label: str,
    image_id: str,
    image_name: str,
    hostname: str,
    ssh_public_key: str | None,
    months: int,
    provider_monthly_cost: Decimal,
) -> Order:
    monthly = customer_monthly_price(provider_monthly_cost)
    total = period_price(monthly, months)
    order = Order(
        user_id=user.id,
        provider=provider,
        region_id=region_id,
        region_name=region_name,
        plan_id=plan_id,
        plan_label=plan_label,
        image_id=image_id,
        image_name=image_name,
        hostname=hostname,
        ssh_public_key=ssh_public_key,
        months=months,
        provider_monthly_cost=provider_monthly_cost,
        total_price=total,
    )
    session.add(order)
    await session.flush()
    logger.info("Order #{} created for user {} (total {})", order.id, user.id, total)
    return order


async def pay_order(session: AsyncSession, user: User, order: Order) -> None:
    """Charge order price from the internal balance. Raises InsufficientBalanceError."""
    if order.status is not OrderStatus.PENDING:
        raise ValueError(f"Order #{order.id} is not payable (status={order.status.value})")
    await apply_transaction(
        session,
        user,
        -order.total_price,
        TransactionType.PURCHASE,
        f"Оплата заказа #{order.id} ({order.plan_label}, {order.months} мес.)",
    )
    order.status = OrderStatus.PAID
    await session.flush()
    await _maybe_pay_referral_bonus(session, user, order)


async def refund_order(session: AsyncSession, order: Order, reason: str) -> None:
    """Full refund on provisioning failure."""
    user = await session.get(User, order.user_id)
    if user is None:
        return
    await apply_transaction(
        session,
        user,
        order.total_price,
        TransactionType.REFUND,
        f"Возврат за заказ #{order.id}: {reason}",
    )
    order.status = OrderStatus.FAILED
    order.error_message = reason
    await session.flush()


async def _maybe_pay_referral_bonus(session: AsyncSession, user: User, order: Order) -> None:
    """Начисляет рефереру бонус с ПЕРВОЙ покупки реферала."""
    if user.referral_bonus_paid or not user.referrer_id:
        return
    referrer = await session.get(User, user.referrer_id)
    if referrer is None or referrer.is_banned:
        return
    percent = get_settings().referral_bonus_percent
    bonus = (order.total_price * percent / Decimal(100)).quantize(Decimal("0.01"))
    if bonus <= 0:
        return
    await apply_transaction(
        session,
        referrer,
        bonus,
        TransactionType.REFERRAL_BONUS,
        f"Реферальный бонус за первую покупку пользователя #{user.id}",
    )
    user.referral_bonus_paid = True
    logger.info("Referral bonus {} paid to user {} for order #{}", bonus, referrer.id, order.id)


async def get_user_orders(session: AsyncSession, user_id: int, limit: int = 20) -> list[Order]:
    result = await session.scalars(
        select(Order).where(Order.user_id == user_id).order_by(Order.id.desc()).limit(limit)
    )
    return list(result)


__all__ = [
    "create_order",
    "pay_order",
    "refund_order",
    "get_user_orders",
    "InsufficientBalanceError",
]
