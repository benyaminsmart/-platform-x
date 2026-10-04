"""Referral schemas — new engine (Phase 77)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ---------- Codes ----------


class ReferralCodePublic(BaseModel):
    id: str
    code: str
    is_default: bool
    is_active: bool
    label: str | None = None
    expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Relationships ----------


class ReferralRelationshipPublic(BaseModel):
    id: str
    status: str
    referrer_user_id: str
    referred_user_id: str
    created_at: datetime
    registered_at: datetime | None = None
    verified_at: datetime | None = None
    qualified_at: datetime | None = None
    rewarded_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReferralRewardPublic(BaseModel):
    id: str
    side: str
    amount: Decimal
    currency: str
    status: str
    issued_at: datetime | None = None
    reversed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------- Me ----------


class ReferralsMe(BaseModel):
    """Summary for GET /referrals/me."""

    referral_code: str
    referred_count: int
    completed_count: int
    pending_count: int
    total_referral_credit: Decimal
    referrals: list[ReferralRelationshipPublic]


# ---------- Requests ----------


class ApplyReferralRequest(BaseModel):
    referral_code: str = Field(min_length=1, max_length=50)


class GenerateReferralCodeRequest(BaseModel):
    label: str | None = Field(default=None, max_length=100)


# ---------- Events ----------


class ReferralEventPublic(BaseModel):
    id: str
    event_type: str
    from_status: str | None = None
    to_status: str | None = None
    extra: dict
    created_at: datetime

    model_config = {"from_attributes": True}
