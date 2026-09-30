"""PriceLock model — user locks a price for a service for a limited window.

Phase 47 (Wave 3, Blue-Ocean B7 — Predictive Price Locks).

Design:
- A user locks the CURRENT price of a service for N hours (default 48).
- While the lock is active, the user can book at the locked price even if
  the live price increases.
- Expired or consumed locks cannot be used.
- One active lock per (user, service): creating a new one replaces the old.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class PriceLock(UUIDMixin, TimestampMixin, Base):
    """A user's locked price on a service for a limited window."""

    __tablename__ = "price_locks"
    __table_args__ = (
        UniqueConstraint("user_id", "service_id", name="uq_price_lock_user_service"),
        Index("ix_price_locks_user", "user_id", "active"),
        Index("ix_price_locks_expires", "expires_at"),
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

    locked_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)

    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_booking_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    def __repr__(self) -> str:
        return f"<PriceLock user={self.user_id} service={self.service_id} price={self.locked_price}>"
