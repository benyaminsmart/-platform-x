"""Wishlist model — user's saved services across tenants.

Design:
- A user can save any active service (across all tenants).
- Unique constraint (user_id, service_id) to prevent duplicates.
- Optional note per entry.
- No tenant_id needed: user is global, service already has tenant.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Wishlist(UUIDMixin, TimestampMixin, Base):
    """A saved service for a user."""

    __tablename__ = "wishlists"
    __table_args__ = (
        UniqueConstraint("user_id", "service_id", name="uq_wishlist_user_service"),
        Index("ix_wishlists_user", "user_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    service_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("services.id"), index=True, nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<Wishlist user={self.user_id} service={self.service_id}>"
