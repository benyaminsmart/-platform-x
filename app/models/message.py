"""Message model — thread per booking between guest and business.

A thread_id groups messages. For now:
- thread_id = booking_id when a booking exists
- otherwise a UUID for ad-hoc threads

sender_role: "user" | "business"
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Message(UUIDMixin, TimestampMixin, Base):
    """One message in a thread between a guest and a business."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_thread", "thread_id"),
        Index("ix_messages_tenant", "tenant_id"),
        Index("ix_messages_booking", "booking_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    thread_id: Mapped[str] = mapped_column(String(36), nullable=False)

    booking_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sender_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)

    body: Mapped[str] = mapped_column(Text, nullable=False)

    read_at_user: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at_business: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Message thread={self.thread_id} role={self.sender_role}>"
