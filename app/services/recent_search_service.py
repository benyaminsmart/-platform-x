"""Recent search service — save + list + prune."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session as DBSession

from app.models.recent_search import RecentSearch


MAX_KEPT = 10


def save(
    db: DBSession,
    *,
    user_id: str,
    check_in: date | None = None,
    check_out: date | None = None,
    guests: int = 1,
    category: str | None = None,
    location: str | None = None,
    currency: str | None = None,
    sort: str | None = None,
) -> RecentSearch | None:
    """Save a search. Returns None if it has no meaningful filters."""
    if not any([check_in, check_out, category, location]):
        return None

    # dedupe: remove identical recent entry
    existing = (
        db.query(RecentSearch)
        .filter(
            RecentSearch.user_id == user_id,
            RecentSearch.check_in == check_in,
            RecentSearch.check_out == check_out,
            RecentSearch.category == category,
            RecentSearch.location == location,
        )
        .all()
    )
    for row in existing:
        db.delete(row)

    row = RecentSearch(
        user_id=user_id,
        check_in=check_in,
        check_out=check_out,
        guests=max(1, int(guests or 1)),
        category=(category or None) or None,
        location=(location or None) or None,
        currency=(currency or None) or None,
        sort=(sort or None) or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    _prune(db, user_id=user_id)
    return row


def _prune(db: DBSession, *, user_id: str) -> None:
    rows = (
        db.query(RecentSearch)
        .filter(RecentSearch.user_id == user_id)
        .order_by(RecentSearch.created_at.desc())
        .all()
    )
    for row in rows[MAX_KEPT:]:
        db.delete(row)
    db.commit()


def list_recent(db: DBSession, *, user_id: str, limit: int = 10) -> list[RecentSearch]:
    return (
        db.query(RecentSearch)
        .filter(RecentSearch.user_id == user_id)
        .order_by(RecentSearch.created_at.desc())
        .limit(max(1, min(int(limit), MAX_KEPT)))
        .all()
    )


def clear(db: DBSession, *, user_id: str) -> int:
    n = db.query(RecentSearch).filter(RecentSearch.user_id == user_id).delete()
    db.commit()
    return int(n or 0)
