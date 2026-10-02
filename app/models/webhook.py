"""Webhook models — outbound event delivery to tenant endpoints.

Two models:
- Webhook: registration (URL, secret hash, events)
- WebhookDelivery: audit log of each attempt

Signature:
  X-PlatformX-Signature: sha256=<hmac_sha256(secret, body)>
  X-PlatformX-Event: <event_type>
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Webhook(UUIDMixin, TimestampMixin, Base):
    """A tenant webhook registration."""

    __tablename__ = "webhooks"
    __table_args__ = (
        Index("ix_webhooks_tenant_active", "tenant_id", "active"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    secret_hashed: Mapped[str] = mapped_column(String(128), nullable=False)

    events: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=True
    )
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<Webhook {self.name} tenant={self.tenant_id} active={self.active}>"


class WebhookDelivery(UUIDMixin, TimestampMixin, Base):
    """One delivery attempt of an event to a webhook."""

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_webhook", "webhook_id"),
        Index("ix_webhook_deliveries_tenant", "tenant_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    webhook_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("webhooks.id"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(default=False, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<WebhookDelivery event={self.event_type} success={self.success}>"
