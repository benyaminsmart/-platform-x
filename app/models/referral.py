"""Referral model — tracks user-to-user referrals."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Referral(UUIDMixin, TimestampMixin, Base):
    """A referral relationship between two users."""

    __tablename__ = "referrals"
    __table_args__ = (
        Index("ix_referrals_tenant_referrer", "tenant_id", "referrer_user_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    referrer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    referred_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    referral_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_booking_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Referral from={self.referrer_user_id} to={self.referred_user_id} status={self.status}>"
