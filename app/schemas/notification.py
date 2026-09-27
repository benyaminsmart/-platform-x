"""Notification schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

NotificationChannel = Literal["email", "whatsapp", "sms", "in_app", "telegram"]
NotificationStatus = Literal["pending", "sent", "failed", "delivered", "read"]


class NotificationPublic(BaseModel):
    """Notification read model."""

    id: str
    tenant_id: str
    user_id: str
    channel: str
    template: str
    subject: str | None
    content: str
    status: str
    provider_reference: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class UnreadCount(BaseModel):
    """Unread notification count."""

    unread: int
