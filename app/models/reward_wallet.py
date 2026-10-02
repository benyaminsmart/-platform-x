"""RewardWallet model — per-user projection of the immutable reward ledger.

Phase 75 (Stage 2, Rewards Foundation).

The wallet is a *derived* view over Reward rows. It is maintained as a
cache for fast reads but must always be rebuildable from the ledger.
Never mutate wallet balances directly from a client — only through
service-layer ledger operations.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class RewardWallet(UUIDMixin, TimestampMixin, Base):
    """Aggregate balances for one user (projection over the ledger)."""

    __tablename__ = "reward_wallets"
    __table_args__ = (
        Index("ix_reward_wallets_user", "user_id", unique=True),
        Index("ix_reward_wallets_tenant", "tenant_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )

    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)

    # Face-value balances (what the user sees)
    available_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    locked_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    expiring_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    referral_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    experience_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    bonus_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)

    # Platform-cost side (what the platform is liable for)
    platform_cost_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    partner_cost_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)

    last_rebuilt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<RewardWallet user={self.user_id} available={self.available_balance}>"
