"""Booking schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import TimestampedModel

BookingType = Literal["room", "table", "treatment", "event", "package", "flight"]
BookingStatus = Literal["pending", "confirmed", "checked_in", "checked_out", "cancelled"]
PaymentStatus = Literal["pending", "paid", "refunded", "failed"]


class BookingCreate(BaseModel):
    """Payload for creating a booking."""

    booking_type: BookingType
    service_id: str | None = None
    service_name: str = Field(min_length=1, max_length=200)
    check_in: date
    check_out: date | None = None
    guests: int = Field(default=1, ge=1, le=50)
    amount: Decimal = Field(gt=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="AED", max_length=10)
    referral_code: str | None = Field(default=None, max_length=50)
    notes: str | None = None

    # Phase 22: opt-in to server-side pricing rules application.
    # Default False to preserve existing behavior for all current callers.
    apply_pricing_rules: bool = False

    @model_validator(mode="after")
    def validate_dates(self) -> "BookingCreate":
        if self.check_out is not None and self.check_out < self.check_in:
            raise ValueError("check_out must be on or after check_in")
        if self.discount > self.amount:
            raise ValueError("discount cannot exceed amount")
        return self


class BookingPublic(TimestampedModel):
    """Booking read model."""

    tenant_id: str
    user_id: str
    booking_type: str
    service_id: str | None
    service_name: str
    check_in: date
    check_out: date | None
    room_number: str | None
    guests: int
    amount: Decimal
    discount: Decimal
    total_amount: Decimal
    currency: str
    status: str
    payment_status: str
    referral_code: str | None
    notes: str | None
    cancelled_at: datetime | None
