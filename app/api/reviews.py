"""Public + user Review API (Phase 28, Step 3).

Public:
  GET  /reviews/tenant/{slug}    list published reviews of a tenant
User (auth required):
  POST /reviews                  create a review for a tenant (X-Tenant-Slug)
  GET  /reviews/mine             list my reviews
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.review import Review
from app.models.tenant import Tenant
from app.models.user import User
from app.services import review_service
from app.services.ai import review_writer


router = APIRouter(prefix="/reviews", tags=["reviews"])


# ---------- Schemas ----------


class ReviewCreateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=5, max_length=4000)
    title: str | None = Field(default=None, max_length=200)
    booking_id: str | None = None
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")
    polish: bool = False  # if true, run AI polish before saving


class ReviewPublic(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    rating: int
    title: str | None
    content: str
    content_polished: str | None
    sentiment: str | None
    sentiment_score: float | None
    language: str
    status: str
    verified: bool
    response_text: str | None
    response_at: str | None
    response_provider: str | None
    created_at: str | None


class ReviewListResponse(BaseModel):
    total: int
    items: list[ReviewPublic]


# ---------- Helpers ----------


def _serialize(r: Review, *, hide_user_id: bool = False) -> ReviewPublic:
    uid = "" if hide_user_id else r.user_id
    return ReviewPublic(
        id=r.id,
        tenant_id=r.tenant_id,
        user_id=uid,
        rating=r.rating,
        title=r.title,
        content=r.content,
        content_polished=r.content_polished,
        sentiment=r.sentiment,
        sentiment_score=r.sentiment_score,
        language=r.language,
        status=r.status,
        verified=r.verified,
        response_text=r.response_text,
        response_at=r.response_at.isoformat() if r.response_at else None,
        response_provider=r.response_provider,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


def _resolve_tenant_by_slug(db: DBSession, slug: str) -> Tenant:
    t = (
        db.query(Tenant)
        .filter(Tenant.slug == slug, Tenant.status == "active", Tenant.deleted_at.is_(None))
        .one_or_none()
    )
    if t is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return t


# ---------- Public ----------


@router.get("/tenant/{slug}", response_model=ReviewListResponse)
@limiter.limit("60/minute")
def public_tenant_reviews(
    request: Request,
    slug: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: DBSession = Depends(get_db),
) -> ReviewListResponse:
    """Public list of published reviews for a tenant."""
    tenant = _resolve_tenant_by_slug(db, slug)
    rows = review_service.list_reviews(db, tenant, include_hidden=False, limit=limit)
    return ReviewListResponse(
        total=len(rows),
        items=[_serialize(r, hide_user_id=False) for r in rows],
    )


# ---------- User (auth) ----------


@router.post("", response_model=ReviewPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_review(
    request: Request,
    payload: ReviewCreateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ReviewPublic:
    """Create a review for the tenant in X-Tenant-Slug."""
    content_polished: str | None = None
    provider = None

    if payload.polish:
        try:
            out = review_writer.polish_review(
                db, tenant=tenant, raw_text=payload.content,
                rating=payload.rating, language=payload.language,
            )
            content_polished = out["content"]
            provider = out["provider"]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        r = review_service.create_review(
            db, tenant=tenant, user=user,
            rating=payload.rating, content=payload.content,
            title=payload.title, booking_id=payload.booking_id,
            language=payload.language, content_polished=content_polished,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if provider:
        r.extra = {**(r.extra or {}), "polish_provider": provider}
        db.commit()

    return _serialize(r)


@router.get("/mine", response_model=ReviewListResponse)
@limiter.limit("30/minute")
def my_reviews(
    request: Request,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ReviewListResponse:
    """All reviews written by the authenticated user."""
    rows = (
        db.query(Review)
        .filter(Review.user_id == user.id)
        .order_by(Review.created_at.desc())
        .limit(100)
        .all()
    )
    return ReviewListResponse(
        total=len(rows),
        items=[_serialize(r) for r in rows],
    )
