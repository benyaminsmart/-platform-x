"""BusinessScore model — monthly AI-driven score per tenant.

Scoring is computed deterministically from real DB data by the
Scoring Engine (Phase 29, Step 2). This model persists a snapshot
per period so the leaderboard is fast and auditable.

Weights (fixed, platform policy):
  Customer Satisfaction  30%
  Service Quality        25%
  Pricing Competitiveness 20%
  Engagement             15%
  Loyalty                10%

Ranks (rank_overall, rank_in_category) are assigned after all scores
for a given period are computed.
"""

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class BusinessScore(UUIDMixin, TimestampMixin, Base):
    """A monthly score snapshot for one tenant."""

    __tablename__ = "business_scores"
    __table_args__ = (
        # one score per tenant per period
        UniqueConstraint("tenant_id", "period_start", "period_end", name="uq_business_score_period"),
        # fast leaderboard query: category + period + score
        Index("ix_business_scores_leaderboard", "category", "period_end", "overall_score"),
        # fast lookup: tenant + period
        Index("ix_business_scores_tenant_period", "tenant_id", "period_end"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Overall 0-100 (weighted sum of the five criteria)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Five criteria, each 0-100
    customer_satisfaction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    service_quality: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pricing_competitiveness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    engagement: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    loyalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Ranks (set after all tenants for the period are scored)
    rank_overall: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_in_category: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Detailed breakdown for transparency / debugging
    criteria_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<BusinessScore tenant={self.tenant_id} "
            f"period={self.period_start}..{self.period_end} "
            f"overall={self.overall_score}>"
        )
