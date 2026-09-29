"""ReviewPhoto model — images attached to a review.

Storage (Phase 39):
- Files stored at app/static/uploads/reviews/<uuid>.<ext>
- Only metadata stored in DB.
- Max 3 photos per review (enforced at service layer).
- Allowed types: image/jpeg, image/png, image/webp.
- Max size: 5 MB.
"""

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class ReviewPhoto(UUIDMixin, TimestampMixin, Base):
    """An image attached to a review."""

    __tablename__ = "review_photos"
    __table_args__ = (
        Index("ix_review_photos_review", "review_id"),
        Index("ix_review_photos_tenant", "tenant_id"),
    )

    review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reviews.id"), index=True, nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<ReviewPhoto review={self.review_id} url={self.url}>"
