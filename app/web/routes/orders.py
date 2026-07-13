"""Orders: list with status filter, force re-provisioning."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus
from app.web.auth import AdminRequired
from app.web.deps import get_db, templates

router = APIRouter(prefix="/orders", dependencies=[AdminRequired])


@router.get("/")
async def orders_list(request: Request, status: str = "", db: AsyncSession = Depends(get_db)):
    stmt = select(Order).order_by(Order.id.desc()).limit(100)
    if status:
        stmt = stmt.where(Order.status == OrderStatus(status))
    orders = list(await db.scalars(stmt))
    template = "partials/orders_table.html" if request.headers.get("HX-Request") else "orders.html"
    return templates.TemplateResponse(
        request,
        template,
        {
            "active_page": "orders",
            "orders": orders,
            "status": status,
            "statuses": [s.value for s in OrderStatus],
        },
    )


@router.post("/{order_id}/reprovision")
async def force_provision(order_id: int, db: AsyncSession = Depends(get_db)):
    """Принудительный повторный запуск provisioning для оплаченного/failed заказа.

    Веб-процесс не имеет доступа к боту, поэтому просто возвращаем заказ
    в статус PAID — фактическое создание выполнит бот-процесс (см. README).
    Для failed-заказа средства должны быть на балансе (их вернул refund) —
    поэтому повторное создание требует ручной проверки.
    """
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(404)
    if order.status not in (OrderStatus.FAILED, OrderStatus.PROVISIONING):
        raise HTTPException(400, "Заказ нельзя перезапустить в текущем статусе")
    order.status = OrderStatus.PAID
    order.error_message = None
    return RedirectResponse("/orders/", status_code=303)
