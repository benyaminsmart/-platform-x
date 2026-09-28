"""User model — end-users (guests) of a tenant."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    """A guest/user belonging to a tenant."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        UniqueConstraint("tenant_id", "phone", name="uq_users_tenant_phone"),
        UniqueConstraint("referral_code", name="uq_users_referral_code"),
        Index("ix_users_tenant_email", "tenant_id", "email"),
        Index("ix_users_tenant_phone", "tenant_id", "phone"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    preferred_currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tier: Mapped[str] = mapped_column(String(50), default="welcome", nullable=False)
    business_role: Mapped[str | None] = mapped_column(String(30), nullable=True)  # owner / manager / staff (null = guest)
    referral_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    referred_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User email={self.email} tenant={self.tenant_id}>"
