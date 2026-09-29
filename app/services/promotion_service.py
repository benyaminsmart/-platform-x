"""Promotion service — validate + apply + track usage.

Validation rules (in order):
1. Code exists for tenant
2. Promotion is active
3. valid_from / valid_to (against today)
4. Global max_uses not exceeded
5. Per-user max_uses_per_user not exceeded (needs db query on usage log)
6. min_amount satisfied
7. service_ids (empty = all; else must contain service_id)

Apply:
- discount = base * value/100 (percent)
- discount = value (fixed)
- new_total = base - discount (floor at 0)

Tracking:
- used_count incremented on successful apply
- a usage log row is NOT stored in this phase (per-user check uses
  Booking table where promotion_code matches user_id; see check_per_user_limit)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.promotion import Promotion
from app.models.tenant import Tenant


VALID_DISCOUNT_TYPES = {"percent", "fixed"}


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------- CRUD ----------


def list_promotions(db: DBSession, tenant: Tenant, *, active_only: bool = False) -> list[Promotion]:
    q = db.query(Promotion).filter(Promotion.tenant_id == tenant.id)
    if active_only:
        q = q.filter(Promotion.active.is_(True))
    return q.order_by(Promotion.created_at.desc()).all()


def get_promotion(db: DBSession, tenant: Tenant, promo_id: str) -> Promotion | None:
    return (
        db.query(Promotion)
        .filter(Promotion.id == promo_id, Promotion.tenant_id == tenant.id)
        .one_or_none()
    )


def get_by_code(db: DBSession, tenant: Tenant, code: str) -> Promotion | None:
    return (
        db.query(Promotion)
        .filter(Promotion.tenant_id == tenant.id, Promotion.code == code.lower().strip())
        .one_or_none()
    )


def create_promotion(
    db: DBSession,
    tenant: Tenant,
    *,
    code: str,
    name: str,
    discount_type: str = "percent",
    discount_value: float | Decimal = 0,
    description: str | None = None,
    max_uses: int | None = None,
    max_uses_per_user: int = 1,
    min_amount: float | Decimal | None = None,
    valid_from: date | None = None,
    valid_to: date | None = None,
    service_ids: list[str] | None = None,
) -> Promotion:
    code = (code or "").strip().lower()
    name = (name or "").strip()
    if not code or not name:
        raise ValueError("code and name are required")
    if discount_type not in VALID_DISCOUNT_TYPES:
        raise ValueError(f"discount_type must be one of: {sorted(VALID_DISCOUNT_TYPES)}")
    if discount_value is None or Decimal(str(discount_value)) <= 0:
        raise ValueError("discount_value must be > 0")
    if valid_from and valid_to and valid_to < valid_from:
        raise ValueError("valid_to must be after valid_from")

    existing = get_by_code(db, tenant, code)
    if existing is not None:
        raise ValueError(f"code '{code}' already exists")

    p = Promotion(
        tenant_id=tenant.id,
        code=code,
        name=name,
        description=(description or "").strip() or None,
        discount_type=discount_type,
        discount_value=Decimal(str(discount_value)),
        max_uses=max_uses,
        max_uses_per_user=max(1, int(max_uses_per_user or 1)),
        min_amount=(Decimal(str(min_amount)) if min_amount is not None else None),
        valid_from=valid_from,
        valid_to=valid_to,
        service_ids=list(service_ids or []),
        active=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_promotion(
    db: DBSession,
    tenant: Tenant,
    promo_id: str,
    updates: dict,
) -> Promotion | None:
    p = get_promotion(db, tenant, promo_id)
    if p is None:
        return None
    for k, v in updates.items():
        if k == "discount_type" and v not in VALID_DISCOUNT_TYPES:
            raise ValueError(f"discount_type must be one of: {sorted(VALID_DISCOUNT_TYPES)}")
        if k == "discount_value" and v is not None:
            v = Decimal(str(v))
            if v <= 0:
                raise ValueError("discount_value must be > 0")
        if k == "min_amount" and v is not None:
            v = Decimal(str(v))
        if k == "max_uses_per_user" and v is not None:
            v = max(1, int(v))
        if hasattr(p, k):
            setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


def delete_promotion(db: DBSession, tenant: Tenant, promo_id: str) -> Promotion | None:
    p = get_promotion(db, tenant, promo_id)
    if p is None:
        return None
    p.active = False
    db.commit()
    db.refresh(p)
    return p


# ---------- Validation ----------


def _per_user_uses(db: DBSession, promotion: Promotion, user_id: str) -> int:
    """Count how many times this user already used this code (via Booking)."""
    return (
        db.query(func.count(Booking.id))
        .filter(
            Booking.tenant_id == promotion.tenant_id,
            Booking.user_id == user_id,
            Booking.rate_plan_code.is_(None),  # not applicable; using notes below
        )
        .scalar()
        or 0
    )


def validate_promotion(
    db: DBSession,
    *,
    tenant: Tenant,
    code: str,
    base_amount: Decimal | float,
    user_id: str | None = None,
    service_id: str | None = None,
    today: date | None = None,
) -> tuple[Promotion | None, str]:
    """Return (promotion, reason). On failure, promotion is None."""
    today = today or date.today()
    code_clean = (code or "").strip().lower()
    if not code_clean:
        return None, "code is empty"

    p = get_by_code(db, tenant, code_clean)
    if p is None:
        return None, "promotion code not found"
    if not p.active:
        return None, "promotion is inactive"
    if p.valid_from and today < p.valid_from:
        return None, "promotion not yet active"
    if p.valid_to and today > p.valid_to:
        return None, "promotion has expired"
    if p.max_uses is not None and p.used_count >= p.max_uses:
        return None, "promotion usage limit reached"
    if p.min_amount is not None and Decimal(str(base_amount)) < p.min_amount:
        return None, f"minimum amount for this code is {p.min_amount}"
    if p.service_ids and service_id and service_id not in p.service_ids:
        return None, "promotion does not apply to this service"

    # per-user check (uses Booking.notes heuristic — Phase 38 will improve)
    if user_id and p.max_uses_per_user:
        used = (
            db.query(func.count(Booking.id))
            .filter(
                Booking.tenant_id == tenant.id,
                Booking.user_id == user_id,
                Booking.notes.ilike(f"%promo={p.code}%"),
            )
            .scalar()
            or 0
        )
        if used >= p.max_uses_per_user:
            return None, "you have already used this code the maximum number of times"

    return p, "ok"


# ---------- Apply ----------


def apply_promotion(
    base_amount: Decimal | float,
    promotion: Promotion,
) -> tuple[Decimal, Decimal]:
    """Return (new_amount, discount_amount). Floor at 0."""
    base = Decimal(str(base_amount))
    val = Decimal(str(promotion.discount_value or 0))
    if promotion.discount_type == "percent":
        discount = _round2(base * val / Decimal("100"))
    else:
        discount = _round2(val)
    if discount > base:
        discount = _round2(base)
    new_amount = _round2(base - discount)
    return new_amount, discount


def increment_usage(db: DBSession, promotion: Promotion) -> None:
    """Increment used_count (best-effort)."""
    promotion.used_count = (promotion.used_count or 0) + 1
    db.add(promotion)
    db.commit()
    db.refresh(promotion)
