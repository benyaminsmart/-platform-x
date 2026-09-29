"""Promotion model — discount codes with conditions.

A Promotion is a tenant-scoped discount code with:
- percent or fixed discount
- optional global usage cap (max_uses)
- optional per-user cap (max_uses_per_user)
- optional minimum booking amount
- optional validity window
- optional service restriction (empty list = all services)
- running used_count

Applying a promotion on a booking:
- discount = base_amount * value/100  (percent)
- discount = value                    (fixed)
- final_amount = base - discount  (floor at 0)
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
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


class Promotion(UUIDMixin, TimestampMixin, Base):
    """A discount code belonging to a tenant."""

    __tablename__ = "promotions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_promotion_tenant_code"),
        Index("ix_promotions_tenant_active", "tenant_id", "active"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # percent | fixed
    discount_type: Mapped[str] = mapped_column(String(20), default="percent", nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    # caps
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_uses_per_user: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    min_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    # empty list => all services
    service_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<Promotion {self.code} tenant={self.tenant_id} active={self.active}>"
