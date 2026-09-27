"""Reward schemas."""

from datetime import datetime

from pydantic import BaseModel


class RewardPublic(BaseModel):
    """Reward transaction read model."""

    id: str
    tenant_id: str
    user_id: str
    reward_type: str
    points: int
    description: str | None
    reference_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RewardsSummary(BaseModel):
    """Summary of a user's reward state."""

    points: int
    tier: str
    next_tier: str | None
    points_to_next_tier: int
    progress_percent: float


class RedeemRequest(BaseModel):
    """Request to redeem a reward."""

    reward_id: str
