"""Referral schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ReferralPublic(BaseModel):
    """Referral read model."""

    id: str
    tenant_id: str
    referrer_user_id: str
    referred_user_id: str
    referral_code: str
    status: str
    reward_points: int
    first_booking_id: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ReferralsMe(BaseModel):
    """Response for GET /referrals/me."""

    referral_code: str
    referred_count: int
    completed_count: int
    total_points_earned: int
    referrals: list[ReferralPublic]


class ApplyReferralRequest(BaseModel):
    """Request to apply a referral code."""

    referral_code: str = Field(min_length=1, max_length=50)
