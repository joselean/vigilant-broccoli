"""Provider abstraction: unified schemas + base HTTP client with retries."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel

from app.models.base import Provider


class ProviderError(Exception):
    """Raised when a provider API call fails after all retries."""

    def __init__(self, provider: Provider, message: str, status_code: int | None = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider.value}] {message}")


class Location(BaseModel):
    id: str
    city: str
    country: str
    flag: str = ""  # emoji флаг страны для красивого вывода


class Plan(BaseModel):
    id: str
    label: str
    vcpus: int
    ram_mb: int
    disk_gb: int
    bandwidth_gb: int | None = None
    monthly_cost_usd: Decimal  # себестоимость у провайдера, уже в USD
    locations: list[str] = []  # id локаций, где план доступен (пусто = везде)


class Image(BaseModel):
    id: str
    name: str
    family: str = ""  # ubuntu / debian / almalinux / ...


class ServerInfo(BaseModel):
    external_id: str
    status: str        # нормализованный: provisioning / active / stopped / error
    main_ip: str | None = None
    raw_status: str = ""


class BaseProvider(ABC):
    """Общий HTTP-клиент с повторными попытками и логированием."""

    provider: Provider
    base_url: str

    def __init__(self, api_key: str, timeout: float = 30.0):
        self._api_key = api_key
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        """HTTP request with exponential backoff on 5xx/429/network errors."""
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url, headers=self._headers(), timeout=self._timeout
                ) as client:
                    resp = await client.request(method, path, json=json, params=params)
                if resp.status_code in (429,) or resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"retryable status {resp.status_code}", request=resp.request, response=resp
                    )
                if resp.status_code >= 400:
                    logger.error(
                        "{} API error {} on {} {}: {}",
                        self.provider.value, resp.status_code, method, path, resp.text[:500],
                    )
                    raise ProviderError(
                        self.provider,
                        f"API error {resp.status_code}: {resp.text[:300]}",
                        resp.status_code,
                    )
                if resp.status_code == 204 or not resp.content:
                    return {}
                return resp.json()  # type: ignore[no-any-return]
            except ProviderError:
                raise
            except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
                last_error = exc
                delay = 2 ** (attempt - 1)
                logger.warning(
                    "{} request {} {} failed (attempt {}/{}): {} — retry in {}s",
                    self.provider.value, method, path, attempt, retries, exc, delay,
                )
                await asyncio.sleep(delay)
        raise ProviderError(self.provider, f"request failed after {retries} retries: {last_error}")

    # --- unified interface -------------------------------------------------

    @abstractmethod
    async def get_locations(self) -> list[Location]: ...

    @abstractmethod
    async def get_plans(self) -> list[Plan]: ...

    @abstractmethod
    async def get_images(self) -> list[Image]: ...

    @abstractmethod
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
    ) -> ServerInfo: ...

    @abstractmethod
    async def get_server(self, external_id: str) -> ServerInfo: ...

    @abstractmethod
    async def reboot_server(self, external_id: str) -> None: ...

    @abstractmethod
    async def reinstall_server(self, external_id: str, image_id: str) -> None: ...

    @abstractmethod
    async def delete_server(self, external_id: str) -> None: ...

    @abstractmethod
    async def reset_password(self, external_id: str) -> str | None:
        """Returns new root password if the provider supports it, else None."""
        ...


COUNTRY_FLAGS = {
    "US": "🇺🇸", "DE": "🇩🇪", "FI": "🇫🇮", "NL": "🇳🇱", "GB": "🇬🇧", "FR": "🇫🇷",
    "SG": "🇸🇬", "JP": "🇯🇵", "AU": "🇦🇺", "CA": "🇨🇦", "PL": "🇵🇱", "SE": "🇸🇪",
    "ES": "🇪🇸", "IN": "🇮🇳", "KR": "🇰🇷", "BR": "🇧🇷", "MX": "🇲🇽", "IL": "🇮🇱",
}


def country_flag(code: str) -> str:
    return COUNTRY_FLAGS.get(code.upper(), "🌍")
