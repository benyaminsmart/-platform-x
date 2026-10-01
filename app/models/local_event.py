"""LocalEvent model — near-term local events (mock data).

Phase 65 (Wave 3, Blue-Ocean B14).

Design:
- Platform-scoped (shared across tenants), like Attraction.
- Mock data source: events are seeded via a script; the real integration
  (Ticketmaster / Google Events) is deferred to the VPS/payment phase.
- Fields include start_at / end_at so the service can filter by date.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class LocalEvent(UUIDMixin, TimestampMixin, Base):
    """A local event near a city (mock for now)."""

    __tablename__ = "local_events"
    __table_args__ = (
        Index("ix_local_events_city", "city"),
        Index("ix_local_events_start_at", "start_at"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # festival, concert, sports, market, ...
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    venue: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ticket_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<LocalEvent {self.name} ({self.category}) at {self.city}>"
