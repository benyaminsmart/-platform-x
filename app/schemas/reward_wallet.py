"""Reward wallet + catalog schemas (Phase 79)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class RewardWalletPublic(BaseModel):
    """Wallet projection read model."""

    currency: str
    available_balance: Decimal
    locked_balance: Decimal
    expiring_balance: Decimal
    referral_balance: Decimal
    experience_balance: Decimal
    bonus_balance: Decimal
    last_rebuilt_at: datetime | None

    model_config = {"from_attributes": True}


class RewardLedgerEntryPublic(BaseModel):
    """One ledger entry in the user's reward history."""

    id: str
    reward_type: str
    amount: Decimal
    currency: str
    funding_source: str
    status: str
    description: str | None
    transaction_id: str | None
    referral_id: str | None
    campaign_id: str | None
    available_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RedeemCatalogItemPublic(BaseModel):
    """A redeem option available to the user."""

    id: str
    name: str
    description: str | None
    points_cost: int
    reward_type: str
    reward_value: Decimal
    category: str | None
    funding_source: str | None

    model_config = {"from_attributes": True}


class RedeemOptionRequest(BaseModel):
    """Request to redeem a catalog option."""

    option_id: str
    reference_id: str | None = None
