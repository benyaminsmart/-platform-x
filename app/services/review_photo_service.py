"""Review Photo service — upload, list, delete.

Storage: app/static/uploads/reviews/<uuid>.<ext>
Max 3 photos per review.
Allowed: image/jpeg, image/png, image/webp.
Max size: 5 MB.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from app.models.review import Review
from app.core.logging_config import get_logger
from app.models.review_photo import ReviewPhoto


UPLOAD_DIR = Path("app/static/uploads/reviews")
MAX_PHOTOS_PER_REVIEW = 3
MAX_FILE_BYTES = 5 * 1024 * 1024
ALLOWED_MIME = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}



logger = get_logger(__name__)

def count_photos(db: DBSession, review_id: str) -> int:
    return db.query(ReviewPhoto).filter(ReviewPhoto.review_id == review_id).count()


def list_photos(db: DBSession, review_id: str) -> list[ReviewPhoto]:
    return (
        db.query(ReviewPhoto)
        .filter(ReviewPhoto.review_id == review_id)
        .order_by(ReviewPhoto.position.asc())
        .all()
    )


def save_photo(
    db: DBSession,
    *,
    review: Review,
    content: bytes,
    content_type: str | None,
) -> ReviewPhoto:
    """Save a photo for a review. Returns the ReviewPhoto row.

    Raises ValueError on validation failures.
    """
    mime = (content_type or "").lower()
    if mime not in ALLOWED_MIME:
        raise ValueError("unsupported file type; use JPG, PNG, or WebP")
    if len(content) == 0:
        raise ValueError("empty file")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("file too large (max 5 MB)")

    existing = count_photos(db, review.id)
    if existing >= MAX_PHOTOS_PER_REVIEW:
        raise ValueError(f"max {MAX_PHOTOS_PER_REVIEW} photos per review")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = ALLOWED_MIME[mime]
    filename = f"{secrets.token_hex(16)}.{ext}"
    target = UPLOAD_DIR / filename
    target.write_bytes(content)

    url = f"/static/uploads/reviews/{filename}"
    row = ReviewPhoto(
        review_id=review.id,
        tenant_id=review.tenant_id,
        url=url,
        position=existing,
        size_bytes=len(content),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_photo(db: DBSession, *, review_id: str, photo_id: str) -> bool:
    row = (
        db.query(ReviewPhoto)
        .filter(ReviewPhoto.id == photo_id, ReviewPhoto.review_id == review_id)
        .one_or_none()
    )
    if row is None:
        return False
    # Best-effort remove file
    try:
        filename = row.url.rsplit("/", 1)[-1]
        (UPLOAD_DIR / filename).unlink(missing_ok=True)
    except Exception:
        logger.warning("Review photo cleanup failed", exc_info=True)
    db.delete(row)
    db.commit()
    return True
