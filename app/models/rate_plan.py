"""RatePlan model — pricing options + conditions per service.

A RatePlan represents an alternate pricing option for a service:
- Room Only, Bed & Breakfast, Half Board, Full Board, Non-refundable, etc.
- Each plan has a price modifier (percent or fixed delta vs base price).
- Each plan has meal plan, refundability, and optional min-nights.

Booking can select a rate plan; the plan's modifier is applied to the
service base price to compute the final booking amount.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class RatePlan(UUIDMixin, TimestampMixin, Base):
    """A pricing option for a service."""

    __tablename__ = "rate_plans"
    __table_args__ = (
        UniqueConstraint("tenant_id", "service_id", "code", name="uq_rate_plan_per_service"),
        Index("ix_rate_plans_tenant_active", "tenant_id", "active"),
        Index("ix_rate_plans_service", "service_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    service_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("services.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)

    # price_modifier_type: "percent" | "fixed"
    price_modifier_type: Mapped[str] = mapped_column(String(20), default="percent", nullable=False)
    # percent: e.g. 15 = +15%, -10 = -10%  |  fixed: e.g. 50 = +50 AED
    price_modifier_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    # meal_plan: none | breakfast | half | full
    meal_plan: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    refundable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_nights: Mapped[int | None] = mapped_column(Integer, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<RatePlan {self.code} service={self.service_id} active={self.active}>"
