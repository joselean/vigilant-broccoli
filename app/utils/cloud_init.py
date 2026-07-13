"""Cloud-init (user_data) generation for initial server setup.

Скрипт первичной настройки: обновление системы, базовые утилиты,
fail2ban + ufw, hostname, SSH-ключи (клиента + мастер-ключ реселлера),
либо установка сгенерированного root-пароля.
"""
from __future__ import annotations

from app.core.config import get_settings


def build_user_data(
    *,
    hostname: str,
    ssh_public_key: str | None,
    root_password: str | None,
) -> str:
    settings = get_settings()

    keys: list[str] = []
    if ssh_public_key:
        keys.append(ssh_public_key.strip())
    # Мастер-ключ реселлера — аварийный доступ к серверам клиентов
    if settings.master_ssh_public_key:
        keys.append(settings.master_ssh_public_key.strip())

    lines: list[str] = [
        "#cloud-config",
        f"hostname: {hostname}",
        "manage_etc_hosts: true",
        "package_update: true",
        "package_upgrade: true",
        "packages:",
        "  - htop",
        "  - fail2ban",
        "  - ufw",
        "  - curl",
        "  - vim",
    ]

    if keys:
        lines.append("ssh_authorized_keys:")
        lines.extend(f"  - {key}" for key in keys)

    if root_password:
        # Пароль устанавливается, только если клиент не дал SSH-ключ
        lines += [
            "ssh_pwauth: true",
            "chpasswd:",
            "  expire: false",
            "  users:",
            "    - name: root",
            f"      password: {root_password}",
            "      type: text",
        ]
    else:
        lines.append("ssh_pwauth: false")

    lines += [
        "runcmd:",
        "  - ufw allow OpenSSH",
        "  - ufw --force enable",
        "  - systemctl enable --now fail2ban",
    ]
    return "\n".join(lines) + "\n"
