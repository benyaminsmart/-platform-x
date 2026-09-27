"""Analytics schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalyticsEventCreate(BaseModel):
    """Payload to track an event."""

    event_type: str = Field(min_length=1, max_length=50)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsEventPublic(BaseModel):
    """Analytics event read model."""

    id: str
    tenant_id: str
    user_id: str | None
    event_type: str
    metadata_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
