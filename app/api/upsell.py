"""AI Upsell Engine API (Phase 56, Step 2).

  GET /services/{service_id}/upsell?language=en       public

Returns up to 3 add-on suggestions for the base service.

NOTE: no 'from __future__ import annotations' in this file.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import upsell_engine as ue


router = APIRouter(prefix="/services", tags=["upsell"])


class SuggestionItem(BaseModel):
    kind: str
    service_id: str
    service_name: str
    service_type: str
    price: float
    currency: str
    description: str | None = None


class UpsellResponse(BaseModel):
    suggestions: list[SuggestionItem]
    rationale: str
    provider: str
    status: str


@router.get("/{service_id}/upsell", response_model=UpsellResponse)
@limiter.limit("30/minute")
def upsell_for_service(
    request: Request,
    service_id: str,
    language: str = Query(default="en", pattern="^(en|ar|fil|hi)$"),
    db: DBSession = Depends(get_db),
) -> UpsellResponse:
    s = db.query(Service).filter(Service.id == service_id).one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Service not found")
    t = db.query(Tenant).filter(Tenant.id == s.tenant_id).one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    from app.core.config import settings
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI disabled")

    try:
        out = ue.suggest(db, tenant=t, base_service_id=service_id, language=language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return UpsellResponse(**out)
