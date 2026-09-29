"""Attraction model — points of interest near a tenant.

Attractions are platform-scoped (not tenant-scoped) so they are shared
across the whole platform. Example: Burj Khalifa is one attraction, used
by every Dubai tenant.
"""

from typing import Any

from sqlalchemy import Float, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Attraction(UUIDMixin, TimestampMixin, Base):
    """A point of interest shared across the platform."""

    __tablename__ = "attractions"
    __table_args__ = (
        Index("ix_attractions_category", "category"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # landmark, museum, beach, park, mall, ...
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<Attraction {self.name} ({self.category})>"
