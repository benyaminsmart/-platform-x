"""Notification model — sent notifications log."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class Notification(UUIDMixin, Base):
    """A notification sent to a user via some channel."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_tenant_user", "tenant_id", "user_id"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_channel", "channel"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    template: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Notification channel={self.channel} template={self.template} status={self.status}>"
