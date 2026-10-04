"""RewardCampaign + RewardCampaignUse models.

Phase 80, Step 1 (plan §17).

A campaign is a conditional bonus on top of the base reward. The
conditions are stored as JSON and evaluated by the campaign engine.

Economic guardrails (plan §18):
- Every campaign has its own budget, usage_limit, user_limit, and
  economic_cap.
- The economic cap is a fraction of the platform's commission on the
  qualifying transaction. The engine never exceeds it.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class RewardCampaign(UUIDMixin, TimestampMixin, Base):
    """A configurable conditional bonus on top of base rewards."""

    __tablename__ = "reward_campaigns"
    __table_args__ = (
        Index("ix_reward_campaigns_active_dates", "active", "start_at", "end_at"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lifecycle
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Conditions (evaluated by the engine) — arbitrary JSON
    # Example keys: category, min_transaction, user_tier, first_booking,
    # repeat_booking, cross_category, geographic_market.
    conditions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Reward shape
    reward_type: Mapped[str] = mapped_column(String(30), nullable=False)  # fixed|percentage|multiplier
    reward_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    funding_source: Mapped[str] = mapped_column(String(20), default="CAMPAIGN", nullable=False)

    # Limits
    budget_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    budget_used: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # total uses
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    user_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # per user

    # Economic cap (fraction of platform commission on the txn, 0..1)
    economic_cap_pct: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), default=Decimal("0.50"), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RewardCampaign {self.name} active={self.active}>"


class RewardCampaignUse(UUIDMixin, Base):
    """One use of a campaign by a user on a booking."""

    __tablename__ = "reward_campaign_uses"
    __table_args__ = (
        Index("ix_reward_campaign_uses_campaign", "campaign_id", "used_at"),
        Index("ix_reward_campaign_uses_user", "user_id", "campaign_id"),
        Index("ix_reward_campaign_uses_booking", "booking_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reward_campaigns.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    booking_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)

    ledger_reward_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rewards.id"), nullable=True
    )

    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RewardCampaignUse campaign={self.campaign_id} user={self.user_id}>"
