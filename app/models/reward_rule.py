"""RewardRule model — configurable per-category reward rates.

Phase 75 (Stage 2, Rewards Foundation, plan §6).

Rates are stored in the DB (not hard-coded) so they can be tuned
without a deploy. The seed provides the initial values from the plan:

    HOTEL       = 1.0% platform-funded reward cost
    FLIGHT      = 0.5%
    EXPERIENCE  = 1.5%
    DINING      = 1.2%
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class RewardRule(UUIDMixin, TimestampMixin, Base):
    """Per-category configuration for reward calculation."""

    __tablename__ = "reward_rules"
    __table_args__ = (
        Index("ix_reward_rules_category_active", "category", "enabled"),
    )

    category: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    platform_reward_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    max_reward_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_transaction_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return f"<RewardRule {self.category} rate={self.platform_reward_rate}>"
