"""Order schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel

OrderStatus = Literal["pending", "preparing", "ready", "delivered", "cancelled"]
OrderPaymentStatus = Literal["pending", "paid", "refunded"]


class OrderCreate(BaseModel):
    """Payload to create an order."""

    service_type: str = Field(min_length=1, max_length=50)
    service_name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(default=1, ge=1, le=100)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="AED", max_length=10)
    notes: str | None = None


class OrderPublic(TimestampedModel):
    """Order read model."""

    tenant_id: str
    user_id: str
    service_type: str
    service_name: str
    quantity: int
    amount: Decimal
    currency: str
    status: str
    payment_status: str
    notes: str | None
    delivered_at: datetime | None
