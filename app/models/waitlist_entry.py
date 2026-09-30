"""WaitlistEntry model — user joins waitlist for a full service/date range.

Phase 48 (Wave 3, Blue-Ocean B8 — Smart Waitlist).

Design:
- A user joins a waitlist for a specific service and a date range
  (check_in / check_out) that is currently full.
- When capacity frees up (cancellation), the earliest (FIFO) waiting
  entry is notified; on-demand check via API.
- One active entry per (user, service, check_in, check_out).
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class WaitlistEntry(UUIDMixin, TimestampMixin, Base):
    """A user's waitlist entry for a full service + date range."""

    __tablename__ = "waitlist_entries"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "service_id", "check_in", "check_out",
            name="uq_waitlist_user_service_dates",
        ),
        Index("ix_waitlist_service_dates", "service_id", "check_in", "check_out"),
        Index("ix_waitlist_user_active", "user_id", "active"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    service_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("services.id"), nullable=False
    )

    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    guests: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    position_at_join: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<WaitlistEntry user={self.user_id} service={self.service_id} {self.check_in}..{self.check_out}>"
