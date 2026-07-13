from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, OrderStatus, Provider, TimestampMixin

if TYPE_CHECKING:
    from app.models.server import Server
    from app.models.user import User


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", values_callable=lambda e: [x.value for x in e]),
        default=OrderStatus.PENDING,
        index=True,
    )

    provider: Mapped[Provider] = mapped_column(
        Enum(Provider, name="provider", values_callable=lambda e: [x.value for x in e])
    )
    region_id: Mapped[str] = mapped_column(String(64))
    region_name: Mapped[str] = mapped_column(String(128), default="")
    plan_id: Mapped[str] = mapped_column(String(64))
    plan_label: Mapped[str] = mapped_column(String(255), default="")
    image_id: Mapped[str] = mapped_column(String(64))
    image_name: Mapped[str] = mapped_column(String(128), default="")
    hostname: Mapped[str] = mapped_column(String(64))
    ssh_public_key: Mapped[str | None] = mapped_column(Text)

    months: Mapped[int] = mapped_column(Integer, default=1)
    # Себестоимость у провайдера (USD/мес) и цена клиента за весь период
    provider_monthly_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    error_message: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="orders")
    server: Mapped[Server | None] = relationship(back_populates="order", uselist=False)

    def __repr__(self) -> str:
        return f"<Order id={self.id} user={self.user_id} {self.status.value}>"
