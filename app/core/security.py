"""Password generation and symmetric encryption for stored server credentials."""
from __future__ import annotations

import secrets
import string

from cryptography.fernet import Fernet

from app.core.config import get_settings

_ALPHABET = string.ascii_letters + string.digits + "!@#%^*-_+="


def _fernet() -> Fernet:
    key = get_settings().encryption_key
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not set — cannot encrypt/decrypt credentials")
    return Fernet(key.encode())


def generate_password(length: int = 20) -> str:
    """Strong random root password (letters + digits + symbols guaranteed)."""
    while True:
        pwd = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
        ):
            return pwd


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def looks_like_ssh_public_key(text: str) -> bool:
    text = text.strip()
    return text.startswith(("ssh-rsa ", "ssh-ed25519 ", "ecdsa-sha2-")) and len(text.split()) >= 2
