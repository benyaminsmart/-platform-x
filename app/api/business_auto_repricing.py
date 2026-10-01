"""Business Auto-Repricing API (Phase 60, Step 2).

Prefix: /business/api/auto-repricing

  GET    /status                            is it enabled?
  POST   /toggle                            enable / disable
  POST   /preview                           preview a live price for a service
  POST   /apply                             apply the suggested price to the service

Auth: business owner/manager (write), any business user (read).

NOTE: no 'from __future__ import annotations' in this file.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import auto_repricing as ar


router = APIRouter(prefix="/business/api/auto-repricing", tags=["business-auto-repricing"])

_WRITE_ROLES = {"owner", "manager"}


def _require_write(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Only owner or manager can change this")


class StatusResponse(BaseModel):
    enabled: bool


class ToggleRequest(BaseModel):
    enabled: bool


class PreviewRequest(BaseModel):
    service_id: str = Field(min_length=1, max_length=36)
    target_date: date | None = None
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class PreviewResponse(BaseModel):
    status: str
    suggested_price: float | None = None
    base_price: float | None = None
    currency: str | None = None
    signals: dict
    rationale: str
    provider: str


class ApplyRequest(BaseModel):
    service_id: str = Field(min_length=1, max_length=36)
    new_price: float = Field(gt=0)
    target_date: date | None = None


@router.get("/status", response_model=StatusResponse)
@limiter.limit("60/minute")
def status(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
) -> StatusResponse:
    return StatusResponse(enabled=ar.is_enabled(tenant))


@router.post("/toggle", response_model=StatusResponse)
@limiter.limit("30/minute")
def toggle(
    request: Request,
    payload: ToggleRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> StatusResponse:
    _require_write(user)
    cfg = dict(tenant.config or {})
    cfg["auto_repricing_enabled"] = bool(payload.enabled)
    tenant.config = cfg
    db.commit()
    return StatusResponse(enabled=bool(payload.enabled))


@router.post("/preview", response_model=PreviewResponse)
@limiter.limit("30/minute")
def preview(
    request: Request,
    payload: PreviewRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> PreviewResponse:
    s = (
        db.query(Service)
        .filter(Service.id == payload.service_id, Service.tenant_id == tenant.id)
        .one_or_none()
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Service not found")
    try:
        out = ar.suggest_price(
            db, tenant=tenant, service=s,
            target_date=payload.target_date, language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PreviewResponse(**out)


@router.post("/apply")
@limiter.limit("15/minute")
def apply_price(
    request: Request,
    payload: ApplyRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    """Apply a new price to the service. Owner/manager only.

    The caller sends the exact new_price they want (usually taken from a
    preview). We do not enforce that it equals the current suggestion —
    the owner is in control.
    """
    _require_write(user)
    s = (
        db.query(Service)
        .filter(Service.id == payload.service_id, Service.tenant_id == tenant.id)
        .one_or_none()
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Service not found")

    from decimal import Decimal, ROUND_HALF_UP
    s.price = Decimal(str(payload.new_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    db.commit()
    db.refresh(s)
    return {
        "applied": True,
        "service_id": s.id,
        "new_price": float(s.price),
        "currency": s.currency,
    }
