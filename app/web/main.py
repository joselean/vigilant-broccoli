"""Web admin panel entrypoint.

Запуск: uvicorn app.web.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse

from app.core.logging import setup_logging
from app.web.auth import SESSION_COOKIE, create_session_token, is_authenticated, verify_password
from app.web.deps import templates
from app.web.routes import dashboard, orders, servers, users

setup_logging("web")

app = FastAPI(title="VDS Reseller — Admin", docs_url=None, redoc_url=None)

app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(servers.router)


@app.get("/login")
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if not verify_password(password):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Неверный пароль"}, status_code=401
        )
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(),
        httponly=True,
        samesite="lax",
        max_age=12 * 3600,
    )
    return response


@app.post("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
