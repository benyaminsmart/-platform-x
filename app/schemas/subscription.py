"""Subscription schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel

SubscriptionPlan = Literal["starter", "professional", "enterprise"]
SubscriptionStatus = Literal["active", "cancelled", "past_due"]
BillingCycle = Literal["monthly", "yearly"]


class SubscriptionPublic(TimestampedModel):
    """Subscription read model."""

    tenant_id: str
    plan: str
    status: str
    price: Decimal
    currency: str
    billing_cycle: str
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: datetime | None


class SubscriptionCreate(BaseModel):
    """Create subscription payload."""

    tenant_id: str
    plan: SubscriptionPlan
    price: Decimal = Field(gt=0)
    currency: str = Field(default="AED", max_length=10)
    billing_cycle: BillingCycle = "monthly"
