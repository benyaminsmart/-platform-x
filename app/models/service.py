"""Service model — sellable items offered by a tenant (rooms, dishes, tours)."""

from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Service(UUIDMixin, TimestampMixin, Base):
    """A sellable service offered by a tenant."""

    __tablename__ = "services"
    __table_args__ = (
        Index("ix_services_tenant_type", "tenant_id", "type"),
        Index("ix_services_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    image_urls: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Service type={self.type} name={self.name} tenant={self.tenant_id}>"
