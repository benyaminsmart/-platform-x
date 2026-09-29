"""Business Review API (Phase 28, Step 3).

Prefix: /business/api/reviews

All endpoints require business auth and are tenant-scoped.
Write actions (hide, respond) restricted to owner/manager.

NOTE: no 'from __future__ import annotations' here.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.review import Review
from app.models.tenant import Tenant
from app.models.user import User
from app.services import review_service
from app.services.ai import review_writer


router = APIRouter(prefix="/business/api/reviews", tags=["business-reviews"])

_WRITE_ROLES = {"owner", "manager"}


# ---------- Schemas ----------


class ReviewItem(BaseModel):
    id: str
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
    items: list[ReviewItem]


class SummaryResponse(BaseModel):
    total: int
    avg_rating: float
    by_rating: dict[str, int]
    by_sentiment: dict[str, int]
    verified_count: int


class RespondRequest(BaseModel):
    response_text: str | None = Field(default=None, max_length=2000)
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")
    tone: str = Field(default="professional", pattern="^(professional|friendly|warm)$")
    use_ai: bool = True


class PolishRequest(BaseModel):
    raw_text: str = Field(min_length=5, max_length=4000)
    rating: int = Field(ge=1, le=5)
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class PolishResponse(BaseModel):
    content: str
    provider: str


# ---------- Helpers ----------


def _require_write(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Only owner or manager can do this")


def _serialize(r: Review) -> ReviewItem:
    return ReviewItem(
        id=r.id,
        user_id=r.user_id,
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


# ---------- Endpoints ----------


@router.get("", response_model=ReviewListResponse)
@limiter.limit("60/minute")
def list_business_reviews(
    request: Request,
    include_hidden: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> ReviewListResponse:
    rows = review_service.list_reviews(db, tenant, include_hidden=include_hidden, limit=limit)
    return ReviewListResponse(total=len(rows), items=[_serialize(r) for r in rows])


@router.get("/summary", response_model=SummaryResponse)
@limiter.limit("60/minute")
def business_reviews_summary(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> SummaryResponse:
    s = review_service.tenant_review_summary(db, tenant)
    return SummaryResponse(
        total=s["total"],
        avg_rating=s["avg_rating"],
        by_rating={str(k): v for k, v in s["by_rating"].items()},
        by_sentiment=s["by_sentiment"],
        verified_count=s["verified_count"],
    )


@router.post("/{review_id}/hide", response_model=ReviewItem)
@limiter.limit("20/minute")
def hide_review(
    request: Request,
    review_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> ReviewItem:
    _require_write(user)
    r = review_service.hide_review(db, tenant, review_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return _serialize(r)


@router.post("/{review_id}/respond", response_model=ReviewItem)
@limiter.limit("20/minute")
def respond_review(
    request: Request,
    review_id: str,
    payload: RespondRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> ReviewItem:
    _require_write(user)
    r = review_service.get_review(db, tenant, review_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Review not found")

    text = (payload.response_text or "").strip()
    provider = "manual"

    if not text and payload.use_ai:
        try:
            out = review_writer.respond_to_review(
                db, tenant=tenant, review=r,
                language=payload.language, tone=payload.tone,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        text = out["response"]
        provider = out["provider"]

    if not text:
        raise HTTPException(status_code=400, detail="response_text or use_ai=true required")

    updated = review_service.set_response(db, tenant, review_id, response_text=text, provider=provider)
    return _serialize(updated)


@router.post("/{review_id}/respond/preview", response_model=PolishResponse)
@limiter.limit("15/minute")
def preview_ai_response(
    request: Request,
    review_id: str,
    payload: RespondRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> PolishResponse:
    """Generate an AI response without saving it."""
    r = review_service.get_review(db, tenant, review_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Review not found")
    try:
        out = review_writer.respond_to_review(
            db, tenant=tenant, review=r,
            language=payload.language, tone=payload.tone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PolishResponse(content=out["response"], provider=out["provider"])


@router.post("/polish", response_model=PolishResponse)
@limiter.limit("15/minute")
def polish_text(
    request: Request,
    payload: PolishRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> PolishResponse:
    """Preview AI-polished version of a review text (does not save)."""
    try:
        out = review_writer.polish_review(
            db, tenant=tenant, raw_text=payload.raw_text,
            rating=payload.rating, language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PolishResponse(content=out["content"], provider=out["provider"])
