from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TicketStatus, TimestampMixin
from app.models.user import User


class SupportTicket(Base, TimestampMixin):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", values_callable=lambda e: [x.value for x in e]),
        default=TicketStatus.OPEN,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship()
