"""PriceAlert model — user watches a service and gets notified on price drop.

Phase 43: alerts are stored and can be checked on-demand via API.
Automatic scheduler (cron) is deferred to VPS phase.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class PriceAlert(UUIDMixin, TimestampMixin, Base):
    """A user's watch on a service's price."""

    __tablename__ = "price_alerts"
    __table_args__ = (
        Index("ix_price_alerts_user", "user_id", "active"),
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

    target_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<PriceAlert user={self.user_id} service={self.service_id} target={self.target_price}>"
