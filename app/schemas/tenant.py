"""Tenant schemas."""

from typing import Any

from app.schemas.common import TimestampedModel


class TenantPublic(TimestampedModel):
    """Public tenant info (for frontend branding)."""

    slug: str
    name: str
    tier: str
    status: str
    config: dict[str, Any]
