"""Trust Score API (Phase 49, Step 2).

  GET /api/trust-score/{tenant_slug}       one tenant's trust score (public)
  POST /api/trust-score/bulk               many tenant scores (public, max 50)

NOTE: no 'from __future__ import annotations' in this file.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.services import trust_score_service as tss


router = APIRouter(prefix="/api/trust-score", tags=["trust-score"])


class ComponentScores(BaseModel):
    rating: float
    volume: float
    verification: float
    responsiveness: float


class Weights(BaseModel):
    rating: float
    volume: float
    verification: float
    responsiveness: float


class TrustScoreResponse(BaseModel):
    tenant_id: str
    tenant_slug: str | None = None
    tenant_name: str | None = None
    score: float
    components: ComponentScores
    weights: Weights
    meta: dict


class BulkRequest(BaseModel):
    tenant_ids: list[str] = Field(min_length=1, max_length=50)


class BulkItem(BaseModel):
    tenant_id: str
    score: float
    components: ComponentScores
    meta: dict


class BulkResponse(BaseModel):
    items: list[BulkItem]


@router.get("/{tenant_slug}", response_model=TrustScoreResponse)
@limiter.limit("60/minute")
def get_trust_score(
    request: Request,
    tenant_slug: str,
    db: DBSession = Depends(get_db),
) -> TrustScoreResponse:
    out = tss.get_by_slug(db, slug=tenant_slug)
    if out is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TrustScoreResponse(**out)


@router.post("/bulk", response_model=BulkResponse)
@limiter.limit("30/minute")
def bulk_trust_score(
    request: Request,
    payload: BulkRequest,
    db: DBSession = Depends(get_db),
) -> BulkResponse:
    data = tss.compute_many(db, tenant_ids=payload.tenant_ids)
    items = []
    for tid, out in data.items():
        items.append(BulkItem(
            tenant_id=tid,
            score=out["score"],
            components=ComponentScores(**out["components"]),
            meta=out["meta"],
        ))
    return BulkResponse(items=items)
