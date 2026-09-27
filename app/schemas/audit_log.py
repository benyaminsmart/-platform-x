"""Audit log schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogPublic(BaseModel):
    """Audit log read model."""

    id: str
    actor_id: str
    actor_type: str
    tenant_id: str | None
    action: str
    target_table: str | None
    target_id: str | None
    changes: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
