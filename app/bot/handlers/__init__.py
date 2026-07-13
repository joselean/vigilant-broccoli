"""Router aggregation. Admin router first — его фильтр пропускает только админов."""
from aiogram import Router

from app.bot.handlers import admin, balance, catalog, profile, servers, start, support


def setup_routers() -> Router:
    root = Router(name="root")
    root.include_router(admin.router)
    root.include_router(start.router)
    root.include_router(catalog.router)
    root.include_router(servers.router)
    root.include_router(balance.router)
    root.include_router(profile.router)
    root.include_router(support.router)
    return root
