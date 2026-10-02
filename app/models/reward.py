"""Reward model — the immutable reward ledger.

Phase 75 (Stage 2, Rewards Foundation).

Every reward operation (earn, redeem, expire, reverse, adjust) creates
a ledger entry here. Entries are never edited or deleted — corrections
create compensating entries.

Ledger fields support:
- Face value (points) and platform/partner cost separation
- Multi-source funding (PLATFORM / PARTNER / CAMPAIGN / REFERRAL / BONUS)
- Lifecycle (PENDING → LOCKED → AVAILABLE → PARTIALLY_USED → USED /
  EXPIRED / REVERSED / CANCELLED)
- Availability and expiration windows
- Traceability back to transaction / referral / campaign
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Numeric, String
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


# Canonical enums (string constants — kept here as the single source
# of truth for the ledger).
FUNDING_SOURCES = ("PLATFORM", "PARTNER", "CAMPAIGN", "REFERRAL", "BONUS")
REWARD_STATUSES = (
    "PENDING", "LOCKED", "AVAILABLE", "PARTIALLY_USED", "USED",
    "EXPIRED", "REVERSED", "CANCELLED",
)


class Reward(UUIDMixin, Base):
    """One immutable ledger entry for a user's reward."""

    __tablename__ = "rewards"
    __table_args__ = (
        Index("ix_rewards_tenant_user", "tenant_id", "user_id"),
        Index("ix_rewards_created_at", "created_at"),
        Index("ix_rewards_user_status", "user_id", "status"),
        Index("ix_rewards_expires_at", "expires_at"),
        Index("ix_rewards_transaction", "transaction_id"),
    )

    # --- Ownership ---
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )

    # --- Core ledger fields (plan §3) ---
    reward_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Amounts (face value + platform cost separation, plan §2)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)
    funding_source: Mapped[str] = mapped_column(String(20), default="PLATFORM", nullable=False)
    platform_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    partner_contribution: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)

    # Lifecycle timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Traceability
    transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    referral_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Legacy points column — kept for backward compatibility with
    # existing reward_service and templates. In the new engine `amount`
    # is authoritative; `points` is set to int(amount) when both are
    # the same value (1 pt = 1 unit) for historical continuity.
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    extra: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Reward type={self.reward_type} status={self.status} "
            f"amount={self.amount} user={self.user_id}>"
        )
