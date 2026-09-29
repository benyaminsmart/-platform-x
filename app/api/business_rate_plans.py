"""Business Rate Plans API (Phase 37, Step 2).

Prefix: /business/api/rate-plans
Owner/manager for writes.

NOTE: no 'from __future__ import annotations'.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import rate_plan_service


router = APIRouter(prefix="/business/api/rate-plans", tags=["business-rate-plans"])

_WRITE_ROLES = {"owner", "manager"}


class RatePlanItem(BaseModel):
    id: str
    service_id: str
    name: str
    code: str
    price_modifier_type: str
    price_modifier_value: str
    meal_plan: str
    refundable: bool
    min_nights: int | None
    description: str | None
    active: bool


class RatePlanListResponse(BaseModel):
    total: int
    items: list[RatePlanItem]


class RatePlanCreateRequest(BaseModel):
    service_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=40)
    price_modifier_type: str = Field(default="percent", max_length=20)
    price_modifier_value: float = 0
    meal_plan: str = Field(default="none", max_length=20)
    refundable: bool = True
    min_nights: int | None = Field(default=None, ge=1, le=365)
    description: str | None = None


class RatePlanUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    price_modifier_type: str | None = Field(default=None, max_length=20)
    price_modifier_value: float | None = None
    meal_plan: str | None = Field(default=None, max_length=20)
    refundable: bool | None = None
    min_nights: int | None = Field(default=None, ge=1, le=365)
    description: str | None = None
    active: bool | None = None


def _ser(rp) -> RatePlanItem:
    return RatePlanItem(
        id=rp.id, service_id=rp.service_id, name=rp.name, code=rp.code,
        price_modifier_type=rp.price_modifier_type,
        price_modifier_value=str(rp.price_modifier_value),
        meal_plan=rp.meal_plan, refundable=rp.refundable,
        min_nights=rp.min_nights, description=rp.description, active=rp.active,
    )


def _require_write(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Only owner or manager can manage rate plans")


@router.get("", response_model=RatePlanListResponse)
@limiter.limit("60/minute")
def list_plans(
    request: Request,
    service_id: str | None = Query(default=None),
    active_only: bool = Query(default=False),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> RatePlanListResponse:
    rows = rate_plan_service.list_plans(db, tenant, service_id=service_id, active_only=active_only)
    return RatePlanListResponse(total=len(rows), items=[_ser(r) for r in rows])


@router.post("", response_model=RatePlanItem)
@limiter.limit("30/minute")
def create_plan(
    request: Request,
    payload: RatePlanCreateRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> RatePlanItem:
    _require_write(user)
    try:
        rp = rate_plan_service.create_plan(
            db, tenant,
            service_id=payload.service_id, name=payload.name, code=payload.code,
            price_modifier_type=payload.price_modifier_type,
            price_modifier_value=payload.price_modifier_value,
            meal_plan=payload.meal_plan, refundable=payload.refundable,
            min_nights=payload.min_nights, description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _ser(rp)


@router.patch("/{plan_id}", response_model=RatePlanItem)
@limiter.limit("30/minute")
def update_plan(
    request: Request,
    plan_id: str,
    payload: RatePlanUpdateRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> RatePlanItem:
    _require_write(user)
    updates = payload.model_dump(exclude_unset=True)
    try:
        rp = rate_plan_service.update_plan(db, tenant, plan_id, updates=updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if rp is None:
        raise HTTPException(status_code=404, detail="Rate plan not found")
    return _ser(rp)


@router.delete("/{plan_id}", response_model=RatePlanItem)
@limiter.limit("30/minute")
def delete_plan(
    request: Request,
    plan_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> RatePlanItem:
    _require_write(user)
    rp = rate_plan_service.delete_plan(db, tenant, plan_id)
    if rp is None:
        raise HTTPException(status_code=404, detail="Rate plan not found")
    return _ser(rp)
