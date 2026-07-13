"""Session-cookie authentication for the web admin panel."""
from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.core.config import get_settings

SESSION_COOKIE = "admin_session"
SESSION_MAX_AGE = 12 * 3600  # 12 часов


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().web_secret_key, salt="admin-auth")


def create_session_token() -> str:
    return _serializer().dumps({"role": "admin"})


def verify_password(password: str) -> bool:
    return hmac.compare_digest(password, get_settings().web_admin_password)


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return False
    try:
        data = _serializer().loads(token, max_age=SESSION_MAX_AGE)
    except BadSignature:
        return False
    return data.get("role") == "admin"


async def require_admin(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"}
        )


AdminRequired = Depends(require_admin)
