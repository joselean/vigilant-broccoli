"""Declarative base and common column types."""
from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Provider(str, enum.Enum):
    VULTR = "vultr"
    HETZNER = "hetzner"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"            # создан, не оплачен
    PAID = "paid"                  # оплачен, ждёт provisioning
    PROVISIONING = "provisioning"  # сервер создаётся у провайдера
    COMPLETED = "completed"        # сервер выдан
    FAILED = "failed"              # ошибка создания (деньги возвращены)
    CANCELLED = "cancelled"


class ServerStatus(str, enum.Enum):
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    STOPPED = "stopped"
    REBOOTING = "rebooting"
    REINSTALLING = "reinstalling"
    EXPIRED = "expired"
    DELETED = "deleted"
    ERROR = "error"


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"            # пополнение баланса
    PURCHASE = "purchase"          # оплата заказа
    RENEWAL = "renewal"            # продление сервера
    REFUND = "refund"              # возврат
    REFERRAL_BONUS = "referral_bonus"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    ANSWERED = "answered"
    CLOSED = "closed"
