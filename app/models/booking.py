"""Booking model — room/service bookings by guests."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Booking(UUIDMixin, TimestampMixin, Base):
    """A booking made by a guest for a room, table, treatment, or package."""

    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bookings_tenant_user", "tenant_id", "user_id"),
        Index("ix_bookings_tenant_check_in", "tenant_id", "check_in"),
        Index("ix_bookings_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )

    booking_type: Mapped[str] = mapped_column(String(50), nullable=False)
    service_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    service_name: Mapped[str] = mapped_column(String(200), nullable=False)

    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date | None] = mapped_column(Date, nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    guests: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)

    status: Mapped[str] = mapped_column(
        String(50), default="pending", index=True, nullable=False
    )
    payment_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )

    referral_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rate_plan_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    rate_plan_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Booking type={self.booking_type} user={self.user_id} status={self.status}>"
