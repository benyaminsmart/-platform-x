"""RecentSearch model — remembers user's last searches.

A search is stored when the user submits the /search page with at least
one filter (check_in, category, location, etc). We keep only the last
N per user (pruned at service layer).
"""

from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class RecentSearch(UUIDMixin, TimestampMixin, Base):
    """One recent search by a user."""

    __tablename__ = "recent_searches"
    __table_args__ = (
        Index("ix_recent_searches_user", "user_id", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )

    check_in: Mapped[date | None] = mapped_column(Date, nullable=True)
    check_out: Mapped[date | None] = mapped_column(Date, nullable=True)
    guests: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(5), nullable=True)
    sort: Mapped[str | None] = mapped_column(String(20), nullable=True)

    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<RecentSearch user={self.user_id} cat={self.category}>"
