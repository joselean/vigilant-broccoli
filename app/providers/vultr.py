"""Vultr API v2 client. Docs: https://www.vultr.com/api/"""
from __future__ import annotations

from decimal import Decimal

from loguru import logger

from app.models.base import Provider
from app.providers.base import (
    BaseProvider,
    Image,
    Location,
    Plan,
    ProviderError,
    ServerInfo,
    country_flag,
)

# Vultr instance power statuses -> normalized statuses
_STATUS_MAP = {
    "pending": "provisioning",
    "installing": "provisioning",
    "active": "active",
    "stopped": "stopped",
    "resizing": "provisioning",
}

# Показываем только актуальные ОС-семейства
_ALLOWED_OS_FAMILIES = ("ubuntu", "debian", "almalinux", "rocky", "centos", "fedora")


class VultrProvider(BaseProvider):
    provider = Provider.VULTR
    base_url = "https://api.vultr.com/v2"

    async def get_locations(self) -> list[Location]:
        data = await self._request("GET", "/regions", params={"per_page": 500})
        return [
            Location(
                id=r["id"],
                city=r["city"],
                country=r["country"],
                flag=country_flag(r["country"]),
            )
            for r in data.get("regions", [])
        ]

    async def get_plans(self) -> list[Plan]:
        data = await self._request("GET", "/plans", params={"type": "vc2", "per_page": 500})
        plans: list[Plan] = []
        for p in data.get("plans", []):
            plans.append(
                Plan(
                    id=p["id"],
                    label=(
                        f"{p['vcpu_count']} vCPU / {p['ram'] // 1024} GB RAM / {p['disk']} GB SSD"
                    ),
                    vcpus=p["vcpu_count"],
                    ram_mb=p["ram"],
                    disk_gb=p["disk"],
                    bandwidth_gb=p.get("bandwidth"),
                    monthly_cost_usd=Decimal(str(p["monthly_cost"])),
                    locations=p.get("locations", []),
                )
            )
        return plans

    async def get_images(self) -> list[Image]:
        data = await self._request("GET", "/os", params={"per_page": 500})
        images: list[Image] = []
        for os_item in data.get("os", []):
            family = os_item.get("family", "").lower()
            if family in _ALLOWED_OS_FAMILIES:
                images.append(Image(id=str(os_item["id"]), name=os_item["name"], family=family))
        return images

    async def create_server(
        self,
        *,
        hostname: str,
        region_id: str,
        plan_id: str,
        image_id: str,
        user_data: str,
        ssh_public_key: str | None = None,
        root_password: str | None = None,
    ) -> ServerInfo:
        import base64

        payload: dict[str, object] = {
            "region": region_id,
            "plan": plan_id,
            "os_id": int(image_id),
            "hostname": hostname,
            "label": hostname,
            "user_data": base64.b64encode(user_data.encode()).decode(),
            "backups": "disabled",
        }
        # Vultr требует SSH-ключ, заранее загруженный в аккаунт
        if ssh_public_key:
            key_id = await self._ensure_ssh_key(hostname, ssh_public_key)
            payload["sshkey_id"] = [key_id]
        data = await self._request("POST", "/instances", json=payload)
        inst = data["instance"]
        logger.info("Vultr instance created: {}", inst["id"])
        return self._to_server_info(inst)

    async def _ensure_ssh_key(self, name: str, public_key: str) -> str:
        """Upload SSH key to the Vultr account (deduplicated by key body)."""
        existing = await self._request("GET", "/ssh-keys", params={"per_page": 500})
        for key in existing.get("ssh_keys", []):
            if key["ssh_key"].strip() == public_key.strip():
                return str(key["id"])
        created = await self._request(
            "POST", "/ssh-keys", json={"name": f"user-{name}", "ssh_key": public_key.strip()}
        )
        return str(created["ssh_key"]["id"])

    async def get_server(self, external_id: str) -> ServerInfo:
        data = await self._request("GET", f"/instances/{external_id}")
        return self._to_server_info(data["instance"])

    async def reboot_server(self, external_id: str) -> None:
        await self._request("POST", f"/instances/{external_id}/reboot")

    async def reinstall_server(self, external_id: str, image_id: str) -> None:
        # Смена ОС + переустановка
        await self._request("PATCH", f"/instances/{external_id}", json={"os_id": int(image_id)})

    async def delete_server(self, external_id: str) -> None:
        await self._request("DELETE", f"/instances/{external_id}")

    async def reset_password(self, external_id: str) -> str | None:
        # Vultr не даёт API для смены root-пароля на работающем сервере
        return None

    @staticmethod
    def _to_server_info(inst: dict) -> ServerInfo:  # type: ignore[type-arg]
        raw = inst.get("status", "pending")
        # server_status уточняет готовность ОС ("installingbooting" -> ещё не готов)
        if raw == "active" and inst.get("server_status") not in ("ok", "installingbooting", None):
            raw = "pending"
        main_ip = inst.get("main_ip") or None
        if main_ip == "0.0.0.0":
            main_ip = None
        return ServerInfo(
            external_id=str(inst["id"]),
            status=_STATUS_MAP.get(raw, "error"),
            main_ip=main_ip,
            raw_status=raw,
        )


__all__ = ["VultrProvider", "ProviderError"]
