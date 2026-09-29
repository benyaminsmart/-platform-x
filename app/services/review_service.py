"""Review service — deterministic sentiment + review operations.

Sentiment is computed by a simple lexicon + rating prior.
No AI here; AI variants live in ai/review_writer.py.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.review import Review
from app.models.tenant import Tenant
from app.models.user import User


# ---------- Sentiment lexicon ----------


_POSITIVE = {
    # English
    "amazing", "excellent", "great", "wonderful", "fantastic", "lovely",
    "perfect", "clean", "friendly", "helpful", "delicious", "comfortable",
    "beautiful", "recommend", "loved", "best", "superb", "outstanding",
    "great value", "friendly staff", "good", "nice", "exceeded",
    # Arabic (basic)
    "رائع", "ممتاز", "جميل", "لطيف", "نظيف", "أحببته", "أنصح",
    # Filipino (basic)
    "maganda", "masarap", "mahusay", "mabait", "malinis", "sulit",
    # Hindi (basic)
    "शानदार", "अच्छा", "सुंदर", "स्वादिष्ट", "साफ", "सिफारिश",
}

_NEGATIVE = {
    # English
    "terrible", "awful", "bad", "dirty", "rude", "slow", "disappointing",
    "worst", "never", "overpriced", "noisy", "cold", "broken", "poor",
    "unhelpful", "disgusting", "hated", "avoid",
    # Arabic (basic)
    "سيء", "سيئة", "مقرف", "بطيء", "غالي", "مزعج",
    # Filipino (basic)
    "pangit", "masama", "marumi", "mabagal", "mahal", "maingay",
    # Hindi (basic)
    "खराब", "गंदा", "महंगा", "धीमा", "बुरा",
}


def _count_hits(text_lower: str, lexicon: set[str]) -> int:
    hits = 0
    for phrase in lexicon:
        if phrase in text_lower:
            hits += 1
    return hits


def compute_sentiment(text: str, rating: int) -> dict[str, Any]:
    """Return {'sentiment': str, 'score': float, 'signals': {...}}.

    score in [-1, 1]; rating prior pulls it toward +/-.
    """
    text_lower = (text or "").lower()
    pos = _count_hits(text_lower, _POSITIVE)
    neg = _count_hits(text_lower, _NEGATIVE)
    total = pos + neg
    if total == 0:
        lexicon_score = 0.0
    else:
        lexicon_score = (pos - neg) / total  # -1..1

    # Rating prior: 3 stars = neutral, 5 = +1, 1 = -1
    rating_score = (rating - 3) / 2.0  # -1..1

    # Weighted: rating 60%, lexicon 40% (rating is a stronger signal)
    score = 0.6 * rating_score + 0.4 * lexicon_score
    score = max(-1.0, min(1.0, score))

    if score >= 0.2:
        label = "positive"
    elif score <= -0.2:
        label = "negative"
    else:
        label = "neutral"

    return {
        "sentiment": label,
        "score": round(score, 3),
        "signals": {"positive_hits": pos, "negative_hits": neg, "rating": rating},
    }


# ---------- Helpers ----------


def _booking_belongs(
    db: DBSession, *, booking_id: str, tenant_id: str, user_id: str
) -> bool:
    b = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.tenant_id == tenant_id,
            Booking.user_id == user_id,
        )
        .one_or_none()
    )
    return b is not None


# ---------- Operations ----------


def create_review(
    db: DBSession,
    *,
    tenant: Tenant,
    user: User,
    rating: int,
    content: str,
    title: str | None = None,
    booking_id: str | None = None,
    language: str = "en",
    content_polished: str | None = None,
) -> Review:
    """Create a review. If booking_id is valid for this user, mark verified."""
    if rating < 1 or rating > 5:
        raise ValueError("rating must be between 1 and 5")
    content = (content or "").strip()
    if len(content) < 5:
        raise ValueError("content must be at least 5 characters")

    verified = False
    if booking_id:
        if not _booking_belongs(db, booking_id=booking_id, tenant_id=tenant.id, user_id=user.id):
            raise ValueError("booking_id does not belong to this user/tenant")
        verified = True

    sent = compute_sentiment(content, rating)

    r = Review(
        tenant_id=tenant.id,
        user_id=user.id,
        booking_id=booking_id,
        rating=rating,
        title=(title or "").strip() or None,
        content=content,
        content_polished=content_polished,
        sentiment=sent["sentiment"],
        sentiment_score=sent["score"],
        language=language or "en",
        status="published",
        verified=verified,
        extra={"sentiment_signals": sent["signals"]},
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_reviews(
    db: DBSession,
    tenant: Tenant,
    *,
    include_hidden: bool = False,
    limit: int = 50,
) -> list[Review]:
    q = db.query(Review).filter(Review.tenant_id == tenant.id)
    if not include_hidden:
        q = q.filter(Review.status == "published")
    return q.order_by(Review.created_at.desc()).limit(limit).all()


def get_review(db: DBSession, tenant: Tenant, review_id: str) -> Review | None:
    return (
        db.query(Review)
        .filter(Review.id == review_id, Review.tenant_id == tenant.id)
        .one_or_none()
    )


def hide_review(db: DBSession, tenant: Tenant, review_id: str) -> Review | None:
    r = get_review(db, tenant, review_id)
    if r is None:
        return None
    r.status = "hidden"
    db.commit()
    db.refresh(r)
    return r


def set_response(
    db: DBSession,
    tenant: Tenant,
    review_id: str,
    *,
    response_text: str,
    provider: str = "manual",
) -> Review | None:
    from datetime import datetime, timezone

    r = get_review(db, tenant, review_id)
    if r is None:
        return None
    r.response_text = (response_text or "").strip() or None
    r.response_at = datetime.now(timezone.utc) if r.response_text else None
    r.response_provider = provider if r.response_text else None
    db.commit()
    db.refresh(r)
    return r


def tenant_review_summary(db: DBSession, tenant: Tenant) -> dict[str, Any]:
    """Return counts + avg rating + sentiment breakdown."""
    from sqlalchemy import func

    rows = (
        db.query(Review.rating, func.count(Review.id))
        .filter(Review.tenant_id == tenant.id, Review.status == "published")
        .group_by(Review.rating)
        .all()
    )
    counts = {int(r): int(c) for r, c in rows}
    total = sum(counts.values())
    weighted = sum(r * c for r, c in counts.items())
    avg = round(weighted / total, 2) if total else 0.0

    sent_rows = (
        db.query(Review.sentiment, func.count(Review.id))
        .filter(Review.tenant_id == tenant.id, Review.status == "published")
        .group_by(Review.sentiment)
        .all()
    )
    sentiments = {(s or "neutral"): int(c) for s, c in sent_rows}

    return {
        "total": total,
        "avg_rating": avg,
        "by_rating": counts,
        "by_sentiment": sentiments,
        "verified_count": (
            db.query(func.count(Review.id))
            .filter(
                Review.tenant_id == tenant.id,
                Review.status == "published",
                Review.verified.is_(True),
            )
            .scalar()
            or 0
        ),
    }
