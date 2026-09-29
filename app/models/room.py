"""Room model — physical room / unit for a tenant.

A Room represents a physical, bookable unit (hotel room, restaurant table,
or any numbered resource).

- Optional link to a Service (the "type" — e.g. Deluxe Suite).
- Unique per tenant: number.
- status: available | occupied | maintenance | inactive.
"""

from typing import Any

from sqlalchemy import (
    JSON,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Room(UUIDMixin, TimestampMixin, Base):
    """A physical unit for a tenant."""

    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("tenant_id", "number", name="uq_room_tenant_number"),
        Index("ix_rooms_tenant_status", "tenant_id", "status"),
        Index("ix_rooms_tenant_service", "tenant_id", "service_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    service_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("services.id"), nullable=True
    )
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="available", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<Room {self.number} tenant={self.tenant_id} status={self.status}>"
