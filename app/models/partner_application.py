"""PartnerApplication model — inbound applications from prospective partners."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class PartnerApplication(UUIDMixin, Base):
    """An application from a business wanting to join Platform-X."""

    __tablename__ = "partner_applications"

    # Business type
    tenant_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Contact info
    contact_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_role: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    whatsapp: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Business info
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instagram: Mapped[str | None] = mapped_column(String(255), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    staff_count: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Plan
    tier_interest: Mapped[str] = mapped_column(String(50), nullable=False, default="professional")
    languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # Free-form
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Type-specific details stored as JSON
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Workflow
    status: Mapped[str] = mapped_column(String(30), default="new", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PartnerApplication {self.business_name} ({self.tenant_type})>"
