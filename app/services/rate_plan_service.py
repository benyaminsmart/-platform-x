"""Rate Plan service — CRUD + price calculation + selection."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session as DBSession

from app.models.rate_plan import RatePlan
from app.models.service import Service
from app.models.tenant import Tenant


VALID_MODIFIER_TYPES = {"percent", "fixed"}
VALID_MEAL_PLANS = {"none", "breakfast", "half", "full"}


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def list_plans(
    db: DBSession,
    tenant: Tenant,
    *,
    service_id: str | None = None,
    active_only: bool = False,
) -> list[RatePlan]:
    q = db.query(RatePlan).filter(RatePlan.tenant_id == tenant.id)
    if service_id:
        q = q.filter(RatePlan.service_id == service_id)
    if active_only:
        q = q.filter(RatePlan.active.is_(True))
    return q.order_by(RatePlan.service_id, RatePlan.code).all()


def get_plan(db: DBSession, tenant: Tenant, plan_id: str) -> RatePlan | None:
    return (
        db.query(RatePlan)
        .filter(RatePlan.id == plan_id, RatePlan.tenant_id == tenant.id)
        .one_or_none()
    )


def create_plan(
    db: DBSession,
    tenant: Tenant,
    *,
    service_id: str,
    name: str,
    code: str,
    price_modifier_type: str = "percent",
    price_modifier_value: float | Decimal = 0,
    meal_plan: str = "none",
    refundable: bool = True,
    min_nights: int | None = None,
    description: str | None = None,
) -> RatePlan:
    name = (name or "").strip()
    code = (code or "").strip().lower()
    if not name:
        raise ValueError("name is required")
    if not code:
        raise ValueError("code is required")
    if price_modifier_type not in VALID_MODIFIER_TYPES:
        raise ValueError(f"price_modifier_type must be one of: {sorted(VALID_MODIFIER_TYPES)}")
    if meal_plan not in VALID_MEAL_PLANS:
        raise ValueError(f"meal_plan must be one of: {sorted(VALID_MEAL_PLANS)}")

    s = (
        db.query(Service)
        .filter(Service.id == service_id, Service.tenant_id == tenant.id)
        .one_or_none()
    )
    if s is None:
        raise ValueError("service not found for this tenant")

    existing = (
        db.query(RatePlan)
        .filter(
            RatePlan.tenant_id == tenant.id,
            RatePlan.service_id == service_id,
            RatePlan.code == code,
        )
        .one_or_none()
    )
    if existing is not None:
        raise ValueError(f"code '{code}' already exists for this service")

    rp = RatePlan(
        tenant_id=tenant.id,
        service_id=service_id,
        name=name,
        code=code,
        price_modifier_type=price_modifier_type,
        price_modifier_value=Decimal(str(price_modifier_value)),
        meal_plan=meal_plan,
        refundable=refundable,
        min_nights=min_nights,
        description=(description or "").strip() or None,
        active=True,
    )
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return rp


def update_plan(
    db: DBSession,
    tenant: Tenant,
    plan_id: str,
    updates: dict,
) -> RatePlan | None:
    rp = get_plan(db, tenant, plan_id)
    if rp is None:
        return None
    for k, v in updates.items():
        if k == "code":
            v = (v or "").strip().lower()
            if not v:
                raise ValueError("code cannot be empty")
            other = (
                db.query(RatePlan)
                .filter(
                    RatePlan.tenant_id == tenant.id,
                    RatePlan.service_id == rp.service_id,
                    RatePlan.code == v,
                    RatePlan.id != rp.id,
                )
                .one_or_none()
            )
            if other is not None:
                raise ValueError(f"code '{v}' already exists for this service")
        if k == "price_modifier_type" and v not in VALID_MODIFIER_TYPES:
            raise ValueError(f"price_modifier_type must be one of: {sorted(VALID_MODIFIER_TYPES)}")
        if k == "meal_plan" and v not in VALID_MEAL_PLANS:
            raise ValueError(f"meal_plan must be one of: {sorted(VALID_MEAL_PLANS)}")
        if k == "price_modifier_value" and v is not None:
            v = Decimal(str(v))
        if hasattr(rp, k):
            setattr(rp, k, v)
    db.commit()
    db.refresh(rp)
    return rp


def delete_plan(db: DBSession, tenant: Tenant, plan_id: str) -> RatePlan | None:
    rp = get_plan(db, tenant, plan_id)
    if rp is None:
        return None
    rp.active = False
    db.commit()
    db.refresh(rp)
    return rp


def apply_plan_to_price(
    base_price: Decimal | float,
    plan: RatePlan,
) -> tuple[Decimal, Decimal]:
    """Return (new_price, delta)."""
    base = Decimal(str(base_price))
    val = Decimal(str(plan.price_modifier_value or 0))
    if plan.price_modifier_type == "percent":
        delta = _round2(base * val / Decimal("100"))
    else:
        delta = _round2(val)
    new_price = _round2(base + delta)
    if new_price < 0:
        new_price = Decimal("0.00")
        delta = _round2(new_price - base)
    return new_price, delta
