"""Application settings loaded from environment (.env)."""
from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    bot_token: str = Field(alias="BOT_TOKEN")
    # Список ID через запятую: "123,456" (NoDecode отключает JSON-парсинг)
    admin_ids: Annotated[list[int], NoDecode] = Field(default_factory=list, alias="ADMIN_IDS")

    # Database
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="vds_reseller", alias="POSTGRES_DB")
    postgres_user: str = Field(default="vds", alias="POSTGRES_USER")
    postgres_password: str = Field(default="vds", alias="POSTGRES_PASSWORD")

    # Providers
    vultr_api_key: str = Field(default="", alias="VULTR_API_KEY")
    hetzner_api_token: str = Field(default="", alias="HETZNER_API_TOKEN")

    # Pricing
    markup_percent: Decimal = Field(default=Decimal("35"), alias="MARKUP_PERCENT")
    eur_usd_rate: Decimal = Field(default=Decimal("1.08"), alias="EUR_USD_RATE")
    period_discounts: dict[int, Decimal] = Field(
        default_factory=lambda: {1: Decimal(0), 3: Decimal(3), 6: Decimal(5), 12: Decimal(10)},
        alias="PERIOD_DISCOUNTS",
    )

    # Security
    encryption_key: str = Field(default="", alias="ENCRYPTION_KEY")
    web_secret_key: str = Field(default="dev-secret", alias="WEB_SECRET_KEY")
    web_admin_password: str = Field(default="admin", alias="WEB_ADMIN_PASSWORD")

    # Web
    web_host: str = Field(default="0.0.0.0", alias="WEB_HOST")
    web_port: int = Field(default=8000, alias="WEB_PORT")

    # Reseller
    master_ssh_public_key: str = Field(default="", alias="MASTER_SSH_PUBLIC_KEY")
    referral_bonus_percent: Decimal = Field(default=Decimal("10"), alias="REFERRAL_BONUS_PERCENT")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, v: object) -> list[int]:
        if isinstance(v, str):
            return [int(x) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v  # type: ignore[return-value]

    @field_validator("period_discounts", mode="before")
    @classmethod
    def _parse_discounts(cls, v: object) -> dict[int, Decimal]:
        if isinstance(v, str):
            raw = json.loads(v)
            return {int(k): Decimal(str(val)) for k, val in raw.items()}
        if isinstance(v, dict):
            return {int(k): Decimal(str(val)) for k, val in v.items()}
        return v  # type: ignore[return-value]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Used by Alembic (psycopg not required — alembic runs async too, kept for tooling)."""
        return self.database_url

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
