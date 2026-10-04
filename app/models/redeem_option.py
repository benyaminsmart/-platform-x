"""RedeemOption model — a reward that users can buy with points.

Phase 44: default policy is intentionally simple and easy to change.
All options live in the DB (seed_populated) so changing pricing later
requires only editing the seed and re-running it.
"""

from decimal import Decimal

from sqlalchemy import Boolean, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class RedeemOption(UUIDMixin, TimestampMixin, Base):
    """A reward option available for points redemption."""

    __tablename__ = "redeem_options"
    __table_args__ = (
        Index("ix_redeem_options_active", "active", "points_cost"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    points_cost: Mapped[int] = mapped_column(Integer, nullable=False)

    # reward_type: "credit" | "discount_pct" | "perk"
    reward_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reward_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Phase 79: economic and category metadata for the real catalog.
    # Nullable to keep old rows valid; the redemption service applies
    # safe defaults when NULL.
    platform_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    funding_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<RedeemOption {self.name} cost={self.points_cost}>"
