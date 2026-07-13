"""Hetzner Cloud API client. Docs: https://docs.hetzner.cloud/"""
from __future__ import annotations

from decimal import Decimal

from loguru import logger

from app.core.pricing import to_usd
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

_STATUS_MAP = {
    "initializing": "provisioning",
    "starting": "provisioning",
    "running": "active",
    "stopping": "stopped",
    "off": "stopped",
    "deleting": "provisioning",
    "rebuilding": "provisioning",
    "migrating": "provisioning",
    "unknown": "error",
}

_ALLOWED_OS = ("ubuntu", "debian", "alma", "rocky", "centos", "fedora")


class HetznerProvider(BaseProvider):
    provider = Provider.HETZNER
    base_url = "https://api.hetzner.cloud/v1"

    async def get_locations(self) -> list[Location]:
        data = await self._request("GET", "/locations")
        return [
            Location(
                id=loc["name"],
                city=loc["city"],
                country=loc["country"],
                flag=country_flag(loc["country"]),
            )
            for loc in data.get("locations", [])
        ]

    async def get_plans(self) -> list[Plan]:
        data = await self._request("GET", "/server_types", params={"per_page": 50})
        plans: list[Plan] = []
        for st in data.get("server_types", []):
            if st.get("deprecated"):
                continue
            prices = st.get("prices", [])
            if not prices:
                continue
            # Берём максимальную цену по локациям как консервативную себестоимость
            monthly_eur = max(Decimal(p["price_monthly"]["net"]) for p in prices)
            locations = [p["location"] for p in prices]
            plans.append(
                Plan(
                    id=str(st["id"]),
                    label=(
                        f"{st['name'].upper()}: {st['cores']} vCPU / "
                        f"{int(st['memory'])} GB RAM / {st['disk']} GB {st['storage_type'].upper()}"
                    ),
                    vcpus=st["cores"],
                    ram_mb=int(st["memory"] * 1024),
                    disk_gb=st["disk"],
                    monthly_cost_usd=to_usd(monthly_eur, "EUR"),
                    locations=locations,
                )
            )
        return plans

    async def get_images(self) -> list[Image]:
        data = await self._request(
            "GET", "/images", params={"type": "system", "status": "available", "per_page": 100}
        )
        images: list[Image] = []
        for img in data.get("images", []):
            flavor = (img.get("os_flavor") or "").lower()
            if any(flavor.startswith(os) for os in _ALLOWED_OS):
                images.append(
                    Image(id=str(img["id"]), name=img.get("description") or img["name"], family=flavor)
                )
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
        payload: dict[str, object] = {
            "name": hostname,
            "location": region_id,
            "server_type": int(plan_id),
            "image": int(image_id),
            "user_data": user_data,
            "start_after_create": True,
        }
        if ssh_public_key:
            key_id = await self._ensure_ssh_key(hostname, ssh_public_key)
            payload["ssh_keys"] = [key_id]
        data = await self._request("POST", "/servers", json=payload)
        server = data["server"]
        logger.info("Hetzner server created: {}", server["id"])
        return self._to_server_info(server)

    async def _ensure_ssh_key(self, name: str, public_key: str) -> int:
        existing = await self._request("GET", "/ssh_keys", params={"per_page": 50})
        for key in existing.get("ssh_keys", []):
            if key["public_key"].strip() == public_key.strip():
                return int(key["id"])
        created = await self._request(
            "POST", "/ssh_keys", json={"name": f"user-{name}", "public_key": public_key.strip()}
        )
        return int(created["ssh_key"]["id"])

    async def get_server(self, external_id: str) -> ServerInfo:
        data = await self._request("GET", f"/servers/{external_id}")
        return self._to_server_info(data["server"])

    async def reboot_server(self, external_id: str) -> None:
        await self._request("POST", f"/servers/{external_id}/actions/reboot")

    async def reinstall_server(self, external_id: str, image_id: str) -> None:
        await self._request(
            "POST", f"/servers/{external_id}/actions/rebuild", json={"image": int(image_id)}
        )

    async def delete_server(self, external_id: str) -> None:
        await self._request("DELETE", f"/servers/{external_id}")

    async def reset_password(self, external_id: str) -> str | None:
        data = await self._request("POST", f"/servers/{external_id}/actions/reset_password")
        return data.get("root_password")

    @staticmethod
    def _to_server_info(server: dict) -> ServerInfo:  # type: ignore[type-arg]
        raw = server.get("status", "unknown")
        ipv4 = (server.get("public_net") or {}).get("ipv4") or {}
        return ServerInfo(
            external_id=str(server["id"]),
            status=_STATUS_MAP.get(raw, "error"),
            main_ip=ipv4.get("ip"),
            raw_status=raw,
        )


__all__ = ["HetznerProvider", "ProviderError"]
