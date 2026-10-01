"""BusinessGroup model — groups multiple tenants under one owner.

Phase 58 (Wave 4, Multi-property Dashboard).

Design:
- A BusinessGroup is owned by a User (the group owner).
- Members are tenants linked via Tenant.group_id.
- Each group has a unique slug for URL use.
- No data-sharing constraints: each tenant keeps its own data; the
  group only provides an aggregated view for the owner.
"""

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class BusinessGroup(UUIDMixin, TimestampMixin, Base):
    """A grouping of multiple tenants under one owner."""

    __tablename__ = "business_groups"
    __table_args__ = (
        Index("ix_business_groups_owner", "owner_user_id"),
    )

    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    owner_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )

    def __repr__(self) -> str:
        return f"<BusinessGroup slug={self.slug} owner={self.owner_user_id}>"
