"""Business Promotions API (Phase 38, Step 3).

Prefix: /business/api/promotions
Owner/manager for writes.

NOTE: no 'from __future__ import annotations'.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import promotion_service


router = APIRouter(prefix="/business/api/promotions", tags=["business-promotions"])

_WRITE_ROLES = {"owner", "manager"}


class PromotionItem(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    discount_type: str
    discount_value: str
    max_uses: int | None
    max_uses_per_user: int
    used_count: int
    min_amount: str | None
    valid_from: str | None
    valid_to: str | None
    service_ids: list[str]
    active: bool


class PromotionListResponse(BaseModel):
    total: int
    items: list[PromotionItem]


class PromotionCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    discount_type: str = Field(default="percent", max_length=20)
    discount_value: float = Field(gt=0)
    max_uses: int | None = Field(default=None, ge=1, le=100000)
    max_uses_per_user: int = Field(default=1, ge=1, le=1000)
    min_amount: float | None = Field(default=None, ge=0)
    valid_from: date | None = None
    valid_to: date | None = None
    service_ids: list[str] = Field(default_factory=list)


class PromotionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    discount_type: str | None = None
    discount_value: float | None = Field(default=None, gt=0)
    max_uses: int | None = Field(default=None, ge=1, le=100000)
    max_uses_per_user: int | None = Field(default=None, ge=1, le=1000)
    min_amount: float | None = Field(default=None, ge=0)
    valid_from: date | None = None
    valid_to: date | None = None
    service_ids: list[str] | None = None
    active: bool | None = None


def _ser(p) -> PromotionItem:
    return PromotionItem(
        id=p.id, code=p.code, name=p.name, description=p.description,
        discount_type=p.discount_type, discount_value=str(p.discount_value),
        max_uses=p.max_uses, max_uses_per_user=p.max_uses_per_user,
        used_count=p.used_count,
        min_amount=(str(p.min_amount) if p.min_amount is not None else None),
        valid_from=(p.valid_from.isoformat() if p.valid_from else None),
        valid_to=(p.valid_to.isoformat() if p.valid_to else None),
        service_ids=list(p.service_ids or []),
        active=bool(p.active),
    )


def _require_write(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Only owner or manager can manage promotions")


@router.get("", response_model=PromotionListResponse)
@limiter.limit("60/minute")
def list_promotions(
    request: Request,
    active_only: bool = Query(default=False),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> PromotionListResponse:
    rows = promotion_service.list_promotions(db, tenant, active_only=active_only)
    return PromotionListResponse(total=len(rows), items=[_ser(p) for p in rows])


@router.post("", response_model=PromotionItem)
@limiter.limit("30/minute")
def create_promotion(
    request: Request,
    payload: PromotionCreateRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> PromotionItem:
    _require_write(user)
    try:
        p = promotion_service.create_promotion(
            db, tenant,
            code=payload.code, name=payload.name,
            discount_type=payload.discount_type, discount_value=payload.discount_value,
            description=payload.description, max_uses=payload.max_uses,
            max_uses_per_user=payload.max_uses_per_user, min_amount=payload.min_amount,
            valid_from=payload.valid_from, valid_to=payload.valid_to,
            service_ids=payload.service_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _ser(p)


@router.patch("/{promo_id}", response_model=PromotionItem)
@limiter.limit("30/minute")
def update_promotion(
    request: Request,
    promo_id: str,
    payload: PromotionUpdateRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> PromotionItem:
    _require_write(user)
    updates = payload.model_dump(exclude_unset=True)
    try:
        p = promotion_service.update_promotion(db, tenant, promo_id, updates=updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if p is None:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return _ser(p)


@router.delete("/{promo_id}", response_model=PromotionItem)
@limiter.limit("30/minute")
def delete_promotion(
    request: Request,
    promo_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> PromotionItem:
    _require_write(user)
    p = promotion_service.delete_promotion(db, tenant, promo_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return _ser(p)


# ---------- Public validate endpoint ----------


class ValidateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    amount: float = Field(ge=0)
    service_id: str | None = None


class ValidateResponse(BaseModel):
    valid: bool
    reason: str
    code: str
    discount_amount: str | None = None
    new_amount: str | None = None
    currency: str = "AED"


@router.post("/validate", response_model=ValidateResponse)
@limiter.limit("30/minute")
def validate_code(
    request: Request,
    payload: ValidateRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> ValidateResponse:
    """Validate a promotion code for a hypothetical amount (preview only)."""
    from decimal import Decimal
    p, reason = promotion_service.validate_promotion(
        db, tenant=tenant, code=payload.code,
        base_amount=Decimal(str(payload.amount)),
        user_id=user.id, service_id=payload.service_id,
    )
    if p is None:
        return ValidateResponse(valid=False, reason=reason, code=payload.code)
    new_amount, discount = promotion_service.apply_promotion(Decimal(str(payload.amount)), p)
    return ValidateResponse(
        valid=True, reason="ok", code=p.code,
        discount_amount=str(discount), new_amount=str(new_amount),
    )
