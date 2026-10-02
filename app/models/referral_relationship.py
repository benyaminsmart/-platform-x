"""ReferralRelationship — a link between a referrer and a referred user.

Phase 77, Step 1b (plan §10).

Lifecycle (plan §10):
    INVITED → REGISTERED → VERIFIED → QUALIFIED → REWARDED
                                                        → REVERSED
                                                        → EXPIRED

The relationship is created when a user applies a referral code (before
or after registration). Rewards are only issued at the QUALIFIED stage,
which requires the referred user's first qualifying transaction
(plan §9-§11).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin

REFERRAL_STATUSES = (
    "INVITED",
    "REGISTERED",
    "VERIFIED",
    "QUALIFIED",
    "REWARDED",
    "REVERSED",
    "EXPIRED",
    "REVIEW",     # plan §12: flagged as suspicious, do not auto-pay
    "CANCELLED",  # hard cancel (spam, duplicate, admin action)
)


class ReferralRelationship(UUIDMixin, TimestampMixin, Base):
    """A referral link from a referrer to a referred user."""

    __tablename__ = "referral_relationships"
    __table_args__ = (
        Index("ix_referral_rel_referrer", "referrer_user_id", "status"),
        Index("ix_referral_rel_referred", "referred_user_id"),
        Index("ix_referral_rel_code", "referral_code_id"),
        Index("ix_referral_rel_tenant", "tenant_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    referral_code_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("referral_codes.id"), nullable=False
    )
    referrer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    referred_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="INVITED", nullable=False
    )

    # Lifecycle timestamps
    registered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    qualified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rewarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reversed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # The booking that qualified this referral
    qualifying_booking_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )

    # Fraud / review reason (plan §12)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ReferralRelationship referrer={self.referrer_user_id} "
            f"referred={self.referred_user_id} status={self.status}>"
        )
