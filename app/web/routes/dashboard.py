"""Dashboard: key metrics and a simple revenue chart."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Server, ServerStatus, Transaction, TransactionType, User
from app.web.auth import AdminRequired
from app.web.deps import get_db, templates

router = APIRouter(dependencies=[AdminRequired])

_INCOME_TYPES = (TransactionType.PURCHASE, TransactionType.RENEWAL)


@router.get("/")
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    users_count = await db.scalar(select(func.count()).select_from(User)) or 0
    active_servers = await db.scalar(
        select(func.count()).select_from(Server).where(Server.status == ServerStatus.ACTIVE)
    ) or 0

    # Выручка за месяц: списания за покупки и продления
    revenue_month = await db.scalar(
        select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
            Transaction.type.in_(_INCOME_TYPES),
            Transaction.created_at >= month_start,
        )
    ) or Decimal(0)

    # Затраты на провайдеров за месяц (по активным серверам, пропорционально)
    provider_costs = await db.scalar(
        select(func.coalesce(func.sum(Server.provider_monthly_cost), 0)).where(
            Server.status == ServerStatus.ACTIVE
        )
    ) or Decimal(0)
    profit_month = revenue_month - provider_costs

    # Выручка по дням за последние 14 дней — для графика
    days: list[str] = []
    values: list[float] = []
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).date()
        day_start = datetime(day.year, day.month, day.day, tzinfo=UTC)
        day_revenue = await db.scalar(
            select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
                Transaction.type.in_(_INCOME_TYPES),
                Transaction.created_at >= day_start,
                Transaction.created_at < day_start + timedelta(days=1),
            )
        ) or Decimal(0)
        days.append(day.strftime("%d.%m"))
        values.append(float(day_revenue))

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active_page": "dashboard",
            "users_count": users_count,
            "active_servers": active_servers,
            "revenue_month": revenue_month,
            "provider_costs": provider_costs,
            "profit_month": profit_month,
            "chart_days": days,
            "chart_values": values,
        },
    )
