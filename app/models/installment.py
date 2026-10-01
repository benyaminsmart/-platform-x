"""Installment models — split a booking payment into 2-3 installments.

Phase 57 (Wave 4, Split Payment).

Design:
- One InstallmentPlan per booking (unique). Owner = user.
- Plan has N installments (2 or 3). Each Installment has:
    sequence (1-based), amount, currency, due_date (optional), status
    status: pending | paid | overdue | cancelled
- Installment 1 (down payment) must be paid to keep the booking alive.
- The booking is only fully settled once every installment is paid.
- Auto-charge is NOT performed. The user must pay each installment
  via the existing payment flow. Reminders are deferred to Phase 11.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date, DateTime, ForeignKey, Index, Integer, Numeric, String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class InstallmentPlan(UUIDMixin, TimestampMixin, Base):
    """A payment plan that splits a booking into installments."""

    __tablename__ = "installment_plans"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_installment_plan_booking"),
        Index("ix_installment_plans_user", "user_id"),
        Index("ix_installment_plans_tenant", "tenant_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    booking_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bookings.id"), nullable=False
    )

    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)
    n_installments: Mapped[int] = mapped_column(Integer, nullable=False)

    # draft | active | completed | cancelled
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<InstallmentPlan booking={self.booking_id} n={self.n_installments} status={self.status}>"


class Installment(UUIDMixin, TimestampMixin, Base):
    """One installment within a plan."""

    __tablename__ = "installments"
    __table_args__ = (
        UniqueConstraint("plan_id", "sequence", name="uq_installment_plan_seq"),
        Index("ix_installments_plan", "plan_id"),
        Index("ix_installments_status", "status"),
    )

    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("installment_plans.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # pending | paid | overdue | cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    def __repr__(self) -> str:
        return f"<Installment plan={self.plan_id} seq={self.sequence} status={self.status}>"
