"""Pricing Rules service — evaluate and apply dynamic pricing rules.

Design principles:
- Rules are evaluated at price-display time (preview_price).
- Rules are recorded at booking time (record_application).
- Priority order: lower `priority` value = applied first (base adjustments),
  higher value = applied later (fine-grained adjustments).
- Percentage rules are multiplicative; fixed rules are additive.
- All price math is Decimal-based; results are rounded to 2 decimals.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import asc
from sqlalchemy.orm import Session as DBSession

from app.models.pricing_rule import PricingRule, PricingRuleApplication
from app.models.service import Service


SUPPORTED_RULE_TYPES = {
    "weekend",
    "season",
    "urgency",
    "capacity",
    "last_minute",
    "custom",
}

SUPPORTED_ACTION_TYPES = {"percent", "fixed"}


# ---------- Helpers ----------


def _dec(v: Any) -> Decimal:
    """Convert to Decimal safely."""
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _round2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------- CRUD ----------


def list_rules(
    db: DBSession, tenant_id: str, *, active_only: bool = False
) -> list[PricingRule]:
    """List a tenant's pricing rules, ordered by priority asc, then created_at."""
    q = db.query(PricingRule).filter(PricingRule.tenant_id == tenant_id)
    if active_only:
        q = q.filter(PricingRule.active.is_(True))
    return q.order_by(asc(PricingRule.priority), asc(PricingRule.created_at)).all()


# ---------- Rule evaluation ----------


def evaluate_rule(
    rule: PricingRule,
    *,
    service: Service | None,
    check_in: date,
    today: date,
    remaining_capacity: int | None = None,
) -> tuple[bool, str]:
    """Return (applies, reason) for a single rule.

    Callers must have already filtered by active / service_ids / valid dates.
    """
    rtype = rule.rule_type
    cond = rule.conditions or {}

    if rtype == "weekend":
        days = cond.get("days_of_week") or []
        try:
            weekday = check_in.weekday()  # Mon=0..Sun=6
        except Exception:
            return False, "invalid check_in"
        if weekday in days:
            return True, f"check-in falls on weekday {weekday}"
        return False, f"weekday {weekday} not in {days}"

    if rtype == "season":
        f = cond.get("from")
        t = cond.get("to")
        try:
            f_d = date.fromisoformat(f) if f else None
            t_d = date.fromisoformat(t) if t else None
        except Exception:
            return False, "invalid season dates"
        if f_d and check_in < f_d:
            return False, "before season start"
        if t_d and check_in > t_d:
            return False, "after season end"
        return True, "within season window"

    if rtype == "urgency":
        max_ahead = cond.get("days_ahead_max")
        if max_ahead is None:
            return False, "no days_ahead_max"
        days_ahead = (check_in - today).days
        if days_ahead <= int(max_ahead):
            return True, f"{days_ahead} days ahead <= {max_ahead}"
        return False, f"{days_ahead} days ahead > {max_ahead}"

    if rtype == "last_minute":
        max_ahead = cond.get("days_ahead_max")
        if max_ahead is None:
            return False, "no days_ahead_max"
        days_ahead = (check_in - today).days
        if 0 <= days_ahead <= int(max_ahead):
            return True, f"last minute ({days_ahead}d ahead)"
        return False, f"{days_ahead} days ahead not in last-minute window"

    if rtype == "capacity":
        if remaining_capacity is None:
            return False, "no capacity data"
        max_remaining = cond.get("max_remaining")
        if max_remaining is None:
            return False, "no max_remaining"
        if remaining_capacity <= int(max_remaining):
            return True, f"remaining {remaining_capacity} <= {max_remaining}"
        return False, f"remaining {remaining_capacity} > {max_remaining}"

    if rtype == "custom":
        # Custom rules are always eligible; service layer decides semantics.
        return True, "custom rule"

    return False, f"unsupported rule_type: {rtype}"


# ---------- Price computation ----------


def compute_adjusted_price(
    base_price: Decimal, rule: PricingRule
) -> tuple[Decimal, Decimal, Decimal]:
    """Apply a rule's action to a base price.

    Returns (new_price, delta_amount, delta_percent).
    - percent: value is +/- percent of base_price
    - fixed:   value is +/- absolute amount
    """
    action = rule.action or {}
    atype = action.get("type")
    if atype not in SUPPORTED_ACTION_TYPES:
        raise ValueError(f"unsupported action type: {atype}")

    try:
        value = _dec(action.get("value", 0))
    except Exception as exc:
        raise ValueError("invalid action value") from exc

    base = _dec(base_price)

    if atype == "percent":
        delta = _round2(base * value / Decimal("100"))
    else:  # fixed
        delta = _round2(value)

    new_price = _round2(base + delta)

    # Never go below zero
    if new_price < 0:
        new_price = Decimal("0.00")
        delta = _round2(new_price - base)

    delta_percent = (
        _round2((delta / base) * Decimal("100")) if base > 0 else Decimal("0.00")
    )

    return new_price, delta, delta_percent


# ---------- Preview ----------


def preview_price(
    db: DBSession,
    *,
    tenant_id: str,
    service: Service,
    check_in: date,
    today: date | None = None,
    remaining_capacity: int | None = None,
) -> dict[str, Any]:
    """Compute the final price after applying all eligible rules in order.

    Returns:
        {
          "original_price": "500.00",
          "final_price": "575.00",
          "currency": "AED",
          "applied_rules": [
              {"id": ..., "name": ..., "rule_type": ...,
               "before": "500.00", "after": "575.00",
               "delta_amount": "75.00", "delta_percent": "15.00",
               "reason": "..."},
              ...
          ]
        }
    """
    today = today or date.today()
    rules = list_rules(db, tenant_id, active_only=True)

    base = _dec(service.price)
    current = base
    applied: list[dict[str, Any]] = []

    for rule in rules:
        # service filter
        if rule.service_ids and service.id not in rule.service_ids:
            continue
        # valid_from/valid_to filter (against today, not check_in)
        if rule.valid_from and today < rule.valid_from:
            continue
        if rule.valid_to and today > rule.valid_to:
            continue

        applies, reason = evaluate_rule(
            rule,
            service=service,
            check_in=check_in,
            today=today,
            remaining_capacity=remaining_capacity,
        )
        if not applies:
            continue

        before = current
        after, delta, delta_pct = compute_adjusted_price(before, rule)
        current = after

        applied.append(
            {
                "id": rule.id,
                "name": rule.name,
                "rule_type": rule.rule_type,
                "before": str(_round2(before)),
                "after": str(_round2(after)),
                "delta_amount": str(delta),
                "delta_percent": str(delta_pct),
                "reason": reason,
            }
        )

    return {
        "original_price": str(_round2(base)),
        "final_price": str(_round2(current)),
        "currency": service.currency or "AED",
        "applied_rules": applied,
    }


# ---------- Recording ----------


def record_application(
    db: DBSession,
    *,
    tenant_id: str,
    rule_id: str,
    original_price: Any,
    adjusted_price: Any,
    delta_amount: Any,
    delta_percent: Any,
    currency: str = "AED",
    service_id: str | None = None,
    booking_id: str | None = None,
    note: str | None = None,
) -> PricingRuleApplication:
    """Persist an application audit record and commit."""
    app = PricingRuleApplication(
        tenant_id=tenant_id,
        rule_id=rule_id,
        service_id=service_id,
        booking_id=booking_id,
        original_price=str(_round2(_dec(original_price))),
        adjusted_price=str(_round2(_dec(adjusted_price))),
        delta_amount=str(_round2(_dec(delta_amount))),
        delta_percent=str(_round2(_dec(delta_percent))),
        currency=currency,
        note=note,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app
