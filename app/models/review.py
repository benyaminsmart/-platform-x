"""Review model — guest reviews of a business (with optional verified booking).

Design (Phase 28):
- A user can review a tenant. If the review is linked to a booking of that
  tenant made by that user, it is marked verified.
- Reviews are published immediately (no moderation queue).
- The business (owner/manager) can respond once; the response can be
  AI-generated or written manually.
- Sentiment: computed deterministically first; AI may refine (Phase 28).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Review(UUIDMixin, TimestampMixin, Base):
    """A guest review for a tenant."""

    __tablename__ = "reviews"
    __table_args__ = (
        Index("ix_reviews_tenant_created", "tenant_id", "created_at"),
        Index("ix_reviews_tenant_rating", "tenant_id", "rating"),
        Index("ix_reviews_user", "user_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    booking_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_polished: Mapped[str | None] = mapped_column(Text, nullable=True)

    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)  # positive|neutral|negative
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1..1

    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # published | hidden
    status: Mapped[str] = mapped_column(String(20), default="published", nullable=False)
    verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    # business response
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ai|manual

    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<Review tenant={self.tenant_id} rating={self.rating} status={self.status}>"
