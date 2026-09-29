"""GroupMember model — members of a group booking.

A group booking:
- One "lead" booking (Booking row) marked as is_group=True (added in this phase).
- One or more GroupMember rows attached to the booking.
- Each member has a share amount (for cost splitting) and a paid flag.

Design (Phase 40):
- We do NOT create separate bookings per member. The lead booking keeps the
  master amount. Members are tracking rows for coordination and cost split.
- Optionally each member can pay directly later (out of scope here).
"""

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class GroupMember(UUIDMixin, TimestampMixin, Base):
    """A member of a group booking."""

    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("booking_id", "email", name="uq_group_member_email"),
        Index("ix_group_members_booking", "booking_id"),
        Index("ix_group_members_tenant", "tenant_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    booking_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bookings.id"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    share_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # optional notes
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    def __repr__(self) -> str:
        return f"<GroupMember {self.email} booking={self.booking_id}>"
