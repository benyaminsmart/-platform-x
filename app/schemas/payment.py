"""Payment schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import TimestampedModel

PaymentStatus = Literal["pending", "success", "failed", "refunded"]
PaymentMethod = Literal["card", "apple_pay", "google_pay", "cash"]
PaymentProvider = str  # telr, stripe, paytabs, checkout, mock


class PaymentIntentRequest(BaseModel):
    """Request to create a payment intent."""

    booking_id: str | None = None
    order_id: str | None = None
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="AED", max_length=10)
    method: PaymentMethod = "card"

    @model_validator(mode="after")
    def require_target(self) -> "PaymentIntentRequest":
        if not self.booking_id and not self.order_id:
            raise ValueError("Either booking_id or order_id is required")
        if self.booking_id and self.order_id:
            raise ValueError("Provide only one of booking_id or order_id")
        return self


class PaymentIntentResponse(BaseModel):
    """Payment intent response with redirect/session info."""

    payment_id: str
    provider: str
    provider_reference: str
    status: str
    amount: Decimal
    currency: str
    # Mock gateway returns a URL that finalizes the payment (dev convenience)
    redirect_url: str


class PaymentPublic(TimestampedModel):
    """Payment read model."""

    tenant_id: str
    user_id: str
    booking_id: str | None
    order_id: str | None
    amount: Decimal
    currency: str
    provider: str
    provider_reference: str
    status: str
    method: str
    metadata_json: dict[str, Any] = Field(alias="metadata_json")
    completed_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}
