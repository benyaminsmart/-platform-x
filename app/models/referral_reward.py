"""ReferralReward — the reward issued for a completed referral.

Phase 77, Step 1d (plan §10-§11).

A ReferralReward tracks the two rewards (referrer + referred) issued
when a relationship reaches the QUALIFIED state. The actual credit is
written to the immutable Reward ledger (Phase 75) with
funding_source="REFERRAL"; this table is a referral-scoped projection
for fast lookup and audit.

Amounts (plan §10):
    referrer = AED 20 (platform credit, non-cash)
    referred = AED 15 (platform credit, non-cash)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin

REFERRAL_REWARD_STATUSES = (
    "PENDING",   # created, waiting for ledger write
    "ISSUED",    # ledger entry written
    "REVERSED",  # reversal ledger entry written
    "CANCELLED", # never issued (flagged / cancelled)
)


class ReferralReward(UUIDMixin, TimestampMixin, Base):
    """A reward issued to one side of a referral relationship."""

    __tablename__ = "referral_rewards"
    __table_args__ = (
        Index("ix_referral_rewards_relationship", "relationship_id"),
        Index("ix_referral_rewards_user", "user_id", "status"),
        Index("ix_referral_rewards_ledger", "ledger_reward_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    relationship_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("referral_relationships.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # 'REFERRER' | 'REFERRED'

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False
    )

    # Link back to the immutable ledger entry in `rewards`
    ledger_reward_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rewards.id"), nullable=True
    )

    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reversed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ReferralReward side={self.side} user={self.user_id} "
            f"amount={self.amount} status={self.status}>"
        )
