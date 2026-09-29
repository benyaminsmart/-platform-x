"""Business Pricing Rules endpoints (Phase 22, Step 3).

Prefix: /business/api/pricing

All endpoints are business-scoped (tenant from the authenticated user).
CRUD is restricted to owner/manager roles; staff can read only.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.pricing_rule import PricingRule
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import pricing_rules as svc

router = APIRouter(prefix="/business/api/pricing", tags=["business-pricing"])

_ALLOWED_RULE_TYPES = sorted(svc.SUPPORTED_RULE_TYPES)
_ALLOWED_ACTION_TYPES = sorted(svc.SUPPORTED_ACTION_TYPES)
_WRITE_ROLES = {"owner", "manager"}


# ---------- Schemas ----------


class PricingRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    rule_type: str = Field(min_length=1, max_length=50)
    conditions: dict[str, Any] = Field(default_factory=dict)
    action: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0)
    active: bool = True
    service_ids: list[str] = Field(default_factory=list)
    valid_from: date | None = None
    valid_to: date | None = None


class PricingRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    rule_type: str | None = None
    conditions: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    priority: int | None = Field(default=None, ge=0)
    active: bool | None = None
    service_ids: list[str] | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class PreviewRequest(BaseModel):
    service_id: str = Field(min_length=1)
    check_in: date
    remaining_capacity: int | None = Field(default=None, ge=0)


# ---------- Helpers ----------


def _serialize(r: PricingRule) -> dict[str, Any]:
    return {
        "id": r.id,
        "name": r.name,
        "description": r.description,
        "rule_type": r.rule_type,
        "conditions": r.conditions,
        "action": r.action,
        "priority": r.priority,
        "active": r.active,
        "service_ids": r.service_ids,
        "valid_from": r.valid_from.isoformat() if r.valid_from else None,
        "valid_to": r.valid_to.isoformat() if r.valid_to else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def _validate_create(payload: PricingRuleCreate) -> None:
    if payload.rule_type not in svc.SUPPORTED_RULE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"rule_type must be one of: {', '.join(_ALLOWED_RULE_TYPES)}",
        )
    atype = (payload.action or {}).get("type")
    if atype not in svc.SUPPORTED_ACTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"action.type must be one of: {', '.join(_ALLOWED_ACTION_TYPES)}",
        )
    if "value" not in (payload.action or {}):
        raise HTTPException(status_code=400, detail="action.value is required")


def _get_owned_rule(db: DBSession, tenant_id: str, rule_id: str) -> PricingRule:
    r = (
        db.query(PricingRule)
        .filter(PricingRule.id == rule_id, PricingRule.tenant_id == tenant_id)
        .one_or_none()
    )
    if r is None:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    return r


def _require_write_role(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only owner or manager can modify pricing rules",
        )


# ---------- Endpoints ----------


@router.get("/rules")
@limiter.limit("60/minute")
def list_rules(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = svc.list_rules(db, tenant.id)
    return [_serialize(r) for r in rows]


@router.post("/rules", status_code=201)
@limiter.limit("20/minute")
def create_rule(
    request: Request,
    payload: PricingRuleCreate,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict[str, Any]:
    _require_write_role(user)
    _validate_create(payload)

    r = PricingRule(
        tenant_id=tenant.id,
        name=payload.name,
        description=payload.description,
        rule_type=payload.rule_type,
        conditions=payload.conditions,
        action=payload.action,
        priority=payload.priority,
        active=payload.active,
        service_ids=payload.service_ids,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        created_by_user_id=user.id,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _serialize(r)


@router.get("/rules/{rule_id}")
@limiter.limit("60/minute")
def get_rule(
    request: Request,
    rule_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict[str, Any]:
    r = _get_owned_rule(db, tenant.id, rule_id)
    return _serialize(r)


@router.patch("/rules/{rule_id}")
@limiter.limit("20/minute")
def update_rule(
    request: Request,
    rule_id: str,
    payload: PricingRuleUpdate,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict[str, Any]:
    _require_write_role(user)
    r = _get_owned_rule(db, tenant.id, rule_id)

    updates = payload.model_dump(exclude_unset=True)
    # Re-validate if rule_type or action is being changed
    if "rule_type" in updates and updates["rule_type"] is not None:
        if updates["rule_type"] not in svc.SUPPORTED_RULE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"rule_type must be one of: {', '.join(_ALLOWED_RULE_TYPES)}",
            )
    if "action" in updates and updates["action"] is not None:
        atype = updates["action"].get("type")
        if atype not in svc.SUPPORTED_ACTION_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"action.type must be one of: {', '.join(_ALLOWED_ACTION_TYPES)}",
            )
        if "value" not in updates["action"]:
            raise HTTPException(status_code=400, detail="action.value is required")

    for k, v in updates.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return _serialize(r)


@router.delete("/rules/{rule_id}")
@limiter.limit("20/minute")
def delete_rule(
    request: Request,
    rule_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict[str, Any]:
    _require_write_role(user)
    r = _get_owned_rule(db, tenant.id, rule_id)
    r.active = False
    db.commit()
    return {"id": r.id, "message": "Pricing rule deactivated"}


@router.post("/preview")
@limiter.limit("60/minute")
def preview(
    request: Request,
    payload: PreviewRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict[str, Any]:
    s = (
        db.query(Service)
        .filter(Service.id == payload.service_id, Service.tenant_id == tenant.id)
        .one_or_none()
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Service not found")

    return svc.preview_price(
        db,
        tenant_id=tenant.id,
        service=s,
        check_in=payload.check_in,
        remaining_capacity=payload.remaining_capacity,
    )
