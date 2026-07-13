"""User management: search, balance adjustment, ban/unban, order history."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Server, ServerStatus, Transaction, TransactionType, User
from app.services.balance import apply_transaction
from app.web.auth import AdminRequired
from app.web.deps import get_db, templates

router = APIRouter(prefix="/users", dependencies=[AdminRequired])


@router.get("/")
async def users_list(request: Request, q: str = "", db: AsyncSession = Depends(get_db)):
    stmt = select(User).order_by(User.id.desc()).limit(100)
    if q:
        filters = [User.username.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%")]
        if q.isdigit():
            filters.append(User.telegram_id == int(q))
        stmt = stmt.where(or_(*filters))
    users = list(await db.scalars(stmt))
    template = "partials/users_table.html" if request.headers.get("HX-Request") else "users.html"
    return templates.TemplateResponse(
        request, template, {"active_page": "users", "users": users, "q": q}
    )


@router.get("/{user_id}")
async def user_detail(request: Request, user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404)
    orders = list(await db.scalars(
        select(Order).where(Order.user_id == user_id).order_by(Order.id.desc()).limit(50)
    ))
    servers = list(await db.scalars(
        select(Server).where(
            Server.user_id == user_id, Server.status != ServerStatus.DELETED
        ).order_by(Server.id.desc())
    ))
    transactions = list(await db.scalars(
        select(Transaction).where(Transaction.user_id == user_id)
        .order_by(Transaction.id.desc()).limit(50)
    ))
    return templates.TemplateResponse(
        request,
        "user_detail.html",
        {
            "active_page": "users",
            "user": user,
            "orders": orders,
            "servers": servers,
            "transactions": transactions,
        },
    )


@router.post("/{user_id}/balance")
async def adjust_balance(
    user_id: int, amount: Decimal = Form(...), db: AsyncSession = Depends(get_db)
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404)
    await apply_transaction(
        db, user, amount, TransactionType.ADMIN_ADJUSTMENT, "Корректировка из веб-админки"
    )
    return RedirectResponse(f"/users/{user_id}", status_code=303)


@router.post("/{user_id}/ban")
async def toggle_ban(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404)
    user.is_banned = not user.is_banned
    return RedirectResponse(f"/users/{user_id}", status_code=303)
