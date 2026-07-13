from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Provider, ServerStatus, TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class Server(Base, TimestampMixin):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))

    provider: Mapped[Provider] = mapped_column(
        Enum(Provider, name="provider", values_callable=lambda e: [x.value for x in e])
    )
    external_server_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[ServerStatus] = mapped_column(
        Enum(ServerStatus, name="server_status", values_callable=lambda e: [x.value for x in e]),
        default=ServerStatus.PROVISIONING,
        index=True,
    )

    hostname: Mapped[str] = mapped_column(String(64))
    main_ip: Mapped[str | None] = mapped_column(String(45))
    region_id: Mapped[str] = mapped_column(String(64))
    region_name: Mapped[str] = mapped_column(String(128), default="")
    plan_id: Mapped[str] = mapped_column(String(64))
    plan_label: Mapped[str] = mapped_column(String(255), default="")
    image_name: Mapped[str] = mapped_column(String(128), default="")

    vcpus: Mapped[int] = mapped_column(Integer, default=0)
    ram_mb: Mapped[int] = mapped_column(Integer, default=0)
    disk_gb: Mapped[int] = mapped_column(Integer, default=0)

    # Зашифрованный root-пароль (Fernet), если использовался пароль вместо SSH-ключа
    encrypted_password: Mapped[str | None] = mapped_column(Text)
    ssh_public_key: Mapped[str | None] = mapped_column(Text)

    monthly_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # цена клиента USD/мес
    provider_monthly_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    autorenew: Mapped[bool] = mapped_column(Boolean, default=False)

    # Отметки об отправленных уведомлениях об истечении (7 дней / 1 день)
    notified_7d: Mapped[bool] = mapped_column(Boolean, default=False)
    notified_1d: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="servers")
    order: Mapped[Order | None] = relationship(back_populates="server")

    def __repr__(self) -> str:
        return f"<Server id={self.id} {self.provider.value}:{self.external_server_id}>"
