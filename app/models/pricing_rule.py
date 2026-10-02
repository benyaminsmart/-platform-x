"""PricingRule model — dynamic pricing rules owned by a tenant.

A PricingRule describes WHEN to adjust prices (conditions) and HOW (action).
Rules are evaluated at price-display time and locked into the booking at
reservation time. Every application is recorded in PricingRuleApplication
for audit and analytics.

Rule types:
  weekend       — applies on configured days of week
  season        — applies within a date range
  urgency       — applies when booking is made within N days of check-in
  capacity      — applies when available capacity is below/above a threshold
  last_minute   — applies when booking is made less than N days ahead
  custom        — free-form, evaluated by service layer

Conditions JSON shape (examples per type):
  weekend:     {"days_of_week": [5, 6]}
  season:      {"from": "2026-12-01", "to": "2026-12-31"}
  urgency:     {"days_ahead_max": 3}
  capacity:    {"max_remaining": 2}   # applies when remaining capacity <= this
  last_minute: {"days_ahead_max": 2}

Action JSON shape:
  {"type": "percent", "value": 15}     # +15%
  {"type": "percent", "value": -20}    # -20%
  {"type": "fixed",   "value": 50}     # +50 AED
  {"type": "fixed",   "value": -30}    # -30 AED
"""

from datetime import date
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class PricingRule(UUIDMixin, TimestampMixin, Base):
    """A pricing rule belonging to one tenant."""

    __tablename__ = "pricing_rules"
    __table_args__ = (
        Index("ix_pricing_rules_tenant_active", "tenant_id", "active"),
        Index("ix_pricing_rules_tenant_priority", "tenant_id", "priority"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    conditions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    action: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Empty list = applies to all services of this tenant
    service_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=True
    )

    def __repr__(self) -> str:
        return f"<PricingRule {self.name} type={self.rule_type} active={self.active}>"


class PricingRuleApplication(UUIDMixin, TimestampMixin, Base):
    """Audit record for a single application of a rule to a booking.

    Created when a rule is applied at booking time (not at preview time).
    Keeps the original and adjusted price for analytics and dispute resolution.
    """

    __tablename__ = "pricing_rule_applications"
    __table_args__ = (
        Index("ix_pricing_apps_tenant", "tenant_id"),
        Index("ix_pricing_apps_booking", "booking_id"),
        Index("ix_pricing_apps_rule", "rule_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pricing_rules.id"), index=True, nullable=False
    )
    service_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    booking_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    original_price: Mapped[str] = mapped_column(String(30), nullable=False)
    adjusted_price: Mapped[str] = mapped_column(String(30), nullable=False)
    delta_amount: Mapped[str] = mapped_column(String(30), nullable=False)
    delta_percent: Mapped[str] = mapped_column(String(30), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PricingRuleApplication rule={self.rule_id} booking={self.booking_id}>"
