"""Recent searches API (Phase 42, Step 1).

  GET    /me/recent-searches
  POST   /me/recent-searches   (save current search)
  DELETE /me/recent-searches   (clear all)
"""

from datetime import date

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services import recent_search_service


router = APIRouter(prefix="/me/recent-searches", tags=["recent-searches"])


class RecentSearchItem(BaseModel):
    id: str
    check_in: str | None
    check_out: str | None
    guests: int
    category: str | None
    location: str | None
    currency: str | None
    sort: str | None
    created_at: str | None


class RecentSearchCreate(BaseModel):
    check_in: date | None = None
    check_out: date | None = None
    guests: int = Field(default=1, ge=1, le=50)
    category: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=200)
    currency: str | None = Field(default=None, max_length=5)
    sort: str | None = Field(default=None, max_length=20)


def _ser(r) -> RecentSearchItem:
    return RecentSearchItem(
        id=r.id,
        check_in=(r.check_in.isoformat() if r.check_in else None),
        check_out=(r.check_out.isoformat() if r.check_out else None),
        guests=r.guests,
        category=r.category,
        location=r.location,
        currency=r.currency,
        sort=r.sort,
        created_at=(r.created_at.isoformat() if r.created_at else None),
    )


@router.get("", response_model=list[RecentSearchItem])
@limiter.limit("60/minute")
def list_recent(
    request: Request,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[RecentSearchItem]:
    rows = recent_search_service.list_recent(db, user_id=user.id)
    return [_ser(r) for r in rows]


@router.post("", response_model=RecentSearchItem | None, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def save_recent(
    request: Request,
    payload: RecentSearchCreate,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    row = recent_search_service.save(
        db, user_id=user.id,
        check_in=payload.check_in, check_out=payload.check_out, guests=payload.guests,
        category=payload.category, location=payload.location,
        currency=payload.currency, sort=payload.sort,
    )
    if row is None:
        return None
    return _ser(row)


@router.delete("")
@limiter.limit("30/minute")
def clear_recent(
    request: Request,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> dict:
    n = recent_search_service.clear(db, user_id=user.id)
    return {"deleted": n}
