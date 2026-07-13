from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, TransactionType

if TYPE_CHECKING:
    from app.models.user import User


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[TransactionType] = mapped_column(
        Enum(
            TransactionType,
            name="transaction_type",
            values_callable=lambda e: [x.value for x in e],
        ),
        index=True,
    )
    # Положительная сумма — зачисление, отрицательная — списание
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str] = mapped_column(String(255), default="")
    # Ссылка на внешний платёж (CryptoBot/YooKassa/Stars) — для будущих интеграций
    external_payment_id: Mapped[str | None] = mapped_column(String(128))

    user: Mapped[User] = relationship(back_populates="transactions")
