"""AnalyticsEvent model — event log for analytics."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class AnalyticsEvent(UUIDMixin, Base):
    """A tracked analytics event."""

    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_tenant_event", "tenant_id", "event_type"),
        Index("ix_analytics_tenant_user", "tenant_id", "user_id"),
        Index("ix_analytics_created_at", "created_at"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AnalyticsEvent type={self.event_type} tenant={self.tenant_id}>"
