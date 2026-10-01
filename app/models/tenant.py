"""Tenant model — a business on the platform."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Tenant(UUIDMixin, TimestampMixin, Base):
    """A business (hotel, restaurant, agency, etc.) on the platform."""

    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    subdomain: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    tier: Mapped[str] = mapped_column(String(50), default="starter", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("business_groups.id"), index=True, nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Tenant slug={self.slug} status={self.status}>"
