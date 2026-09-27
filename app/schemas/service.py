"""Service schemas."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel

ServiceType = str  # room, table, treatment, event, package, flight, dish, tour


class ServicePublic(TimestampedModel):
    """Public service read model."""

    tenant_id: str
    type: str
    name: str
    description: str | None
    price: Decimal
    currency: str
    capacity: int | None
    attributes: dict[str, Any]
    image_urls: list[str]
    status: str
    display_order: int


class ServiceCreate(BaseModel):
    """Admin payload to create a service."""

    type: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: Decimal = Field(ge=0)
    currency: str = Field(default="AED", max_length=10)
    capacity: int | None = Field(default=None, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    image_urls: list[str] = Field(default_factory=list)
    status: str = Field(default="active", max_length=50)
    display_order: int = Field(default=0, ge=0)


class ServiceUpdate(BaseModel):
    """Admin payload to update a service (partial)."""

    type: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=10)
    capacity: int | None = Field(default=None, ge=0)
    attributes: dict[str, Any] | None = None
    image_urls: list[str] | None = None
    status: str | None = Field(default=None, max_length=50)
    display_order: int | None = Field(default=None, ge=0)
