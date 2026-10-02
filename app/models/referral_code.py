"""ReferralCode model — a shareable code owned by a user.

Phase 77, Step 1a (plan §10).

Each user may own one or more referral codes. The code is globally
unique (like `User.referral_code`) so a code can be resolved without a
tenant context. The `tenant_id` records the owning tenant; the
relationship binds the referred user to the referrer's tenant.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class ReferralCode(UUIDMixin, TimestampMixin, Base):
    """A shareable referral code owned by a user."""

    __tablename__ = "referral_codes"
    __table_args__ = (
        Index("ix_referral_codes_user", "user_id"),
        Index("ix_referral_codes_tenant", "tenant_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<ReferralCode code={self.code} user={self.user_id}>"
