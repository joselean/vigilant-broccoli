"""All servers: filters + manual admin actions (reboot / delete / sync)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Provider, Server, ServerStatus
from app.providers import ProviderError, get_provider
from app.web.auth import AdminRequired
from app.web.deps import get_db, templates

router = APIRouter(prefix="/servers", dependencies=[AdminRequired])


@router.get("/")
async def servers_list(
    request: Request,
    provider: str = "",
    status: str = "",
    user_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Server).order_by(Server.id.desc()).limit(200)
    if provider:
        stmt = stmt.where(Server.provider == Provider(provider))
    if status:
        stmt = stmt.where(Server.status == ServerStatus(status))
    if user_id:
        stmt = stmt.where(Server.user_id == user_id)
    servers = list(await db.scalars(stmt))
    template = (
        "partials/servers_table.html" if request.headers.get("HX-Request") else "servers.html"
    )
    return templates.TemplateResponse(
        request,
        template,
        {
            "active_page": "servers",
            "servers": servers,
            "provider": provider,
            "status": status,
            "providers": [p.value for p in Provider],
            "statuses": [s.value for s in ServerStatus],
        },
    )


async def _get_server(db: AsyncSession, server_id: int) -> Server:
    server = await db.get(Server, server_id)
    if server is None:
        raise HTTPException(404)
    return server


@router.post("/{server_id}/reboot")
async def reboot_server(server_id: int, db: AsyncSession = Depends(get_db)):
    server = await _get_server(db, server_id)
    try:
        await get_provider(server.provider).reboot_server(server.external_server_id)
    except ProviderError as exc:
        raise HTTPException(502, str(exc)) from exc
    return RedirectResponse("/servers/", status_code=303)


@router.post("/{server_id}/sync")
async def sync_server(server_id: int, db: AsyncSession = Depends(get_db)):
    server = await _get_server(db, server_id)
    try:
        info = await get_provider(server.provider).get_server(server.external_server_id)
    except ProviderError as exc:
        if exc.status_code == 404:
            server.status = ServerStatus.DELETED
            return RedirectResponse("/servers/", status_code=303)
        raise HTTPException(502, str(exc)) from exc
    if info.main_ip:
        server.main_ip = info.main_ip
    mapping = {
        "active": ServerStatus.ACTIVE,
        "stopped": ServerStatus.STOPPED,
        "provisioning": ServerStatus.PROVISIONING,
        "error": ServerStatus.ERROR,
    }
    server.status = mapping.get(info.status, server.status)
    return RedirectResponse("/servers/", status_code=303)


@router.post("/{server_id}/delete")
async def delete_server(server_id: int, db: AsyncSession = Depends(get_db)):
    server = await _get_server(db, server_id)
    try:
        await get_provider(server.provider).delete_server(server.external_server_id)
    except ProviderError as exc:
        if exc.status_code != 404:
            raise HTTPException(502, str(exc)) from exc
    server.status = ServerStatus.DELETED
    return RedirectResponse("/servers/", status_code=303)
