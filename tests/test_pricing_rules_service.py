"""Tests for the Pricing Rules service (Phase 22, Step 2).

Coverage:
- list_rules ordering by priority
- evaluate_rule for every supported rule_type (positive + negative)
- compute_adjusted_price for percent (positive/negative) + fixed
- preview_price stacking (single + multiple rules in priority order)
- service_ids filter, valid_from/to filter, active filter
- negative-price floor (never below 0)
- record_application persistence
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.pricing_rule import PricingRule, PricingRuleApplication
from app.models.service import Service
from app.models.tenant import Tenant
from app.services import pricing_rules


# ---------- Helpers ----------


def _svc(db: Session, tenant: Tenant, *, typ: str = "room", name: str = "R", price: float = 500) -> Service:
    s = Service(
        tenant_id=tenant.id,
        type=typ,
        name=name,
        price=Decimal(str(price)),
        currency="AED",
        capacity=2,
        attributes={},
        image_urls=[],
        status="active",
        display_order=0,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _rule(
    db: Session,
    tenant: Tenant,
    *,
    name: str = "R",
    rule_type: str = "weekend",
    conditions: dict | None = None,
    action: dict | None = None,
    priority: int = 100,
    active: bool = True,
    service_ids: list[str] | None = None,
    valid_from: date | None = None,
    valid_to: date | None = None,
) -> PricingRule:
    r = PricingRule(
        tenant_id=tenant.id,
        name=name,
        rule_type=rule_type,
        conditions=conditions or {},
        action=action or {"type": "percent", "value": 10},
        priority=priority,
        active=active,
        service_ids=service_ids or [],
        valid_from=valid_from,
        valid_to=valid_to,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


# ---------- list_rules ----------


def test_list_rules_orders_by_priority(db: Session, sample_tenant: Tenant) -> None:
    _rule(db, sample_tenant, name="b", priority=200)
    _rule(db, sample_tenant, name="a", priority=50)
    _rule(db, sample_tenant, name="c", priority=100)
    rows = pricing_rules.list_rules(db, sample_tenant.id)
    assert [r.name for r in rows] == ["a", "c", "b"]


def test_list_rules_active_only(db: Session, sample_tenant: Tenant) -> None:
    _rule(db, sample_tenant, name="on", active=True)
    _rule(db, sample_tenant, name="off", active=False)
    active = pricing_rules.list_rules(db, sample_tenant.id, active_only=True)
    assert [r.name for r in active] == ["on"]


# ---------- evaluate_rule ----------


def test_evaluate_weekend_positive(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, rule_type="weekend", conditions={"days_of_week": [5, 6]})
    # 2026-10-03 is a Saturday (weekday=5)
    applies, reason = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 3), today=date(2026, 10, 1)
    )
    assert applies is True
    assert "weekday 5" in reason


def test_evaluate_weekend_negative(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, rule_type="weekend", conditions={"days_of_week": [5, 6]})
    # 2026-10-01 is a Thursday (weekday=3)
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 1), today=date(2026, 10, 1)
    )
    assert applies is False


def test_evaluate_season(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(
        db, sample_tenant, rule_type="season",
        conditions={"from": "2026-12-01", "to": "2026-12-31"},
    )
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 12, 15), today=date(2026, 11, 1)
    )
    assert applies is True
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 11, 15), today=date(2026, 11, 1)
    )
    assert applies is False
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2027, 1, 15), today=date(2026, 11, 1)
    )
    assert applies is False


def test_evaluate_urgency(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, rule_type="urgency", conditions={"days_ahead_max": 3})
    # check-in 2 days ahead -> applies
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 3), today=date(2026, 10, 1)
    )
    assert applies is True
    # check-in 5 days ahead -> does not apply
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 6), today=date(2026, 10, 1)
    )
    assert applies is False


def test_evaluate_last_minute(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, rule_type="last_minute", conditions={"days_ahead_max": 2})
    # 1 day ahead -> applies
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 2), today=date(2026, 10, 1)
    )
    assert applies is True
    # 3 days ahead -> does not apply
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 4), today=date(2026, 10, 1)
    )
    assert applies is False
    # past check-in -> not last-minute
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 9, 30), today=date(2026, 10, 1)
    )
    assert applies is False


def test_evaluate_capacity(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, rule_type="capacity", conditions={"max_remaining": 2})
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 10), today=date(2026, 10, 1),
        remaining_capacity=1,
    )
    assert applies is True
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 10), today=date(2026, 10, 1),
        remaining_capacity=5,
    )
    assert applies is False
    applies, _ = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 10), today=date(2026, 10, 1),
        remaining_capacity=None,
    )
    assert applies is False


def test_evaluate_custom_always_applies(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, rule_type="custom", conditions={})
    applies, reason = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 10), today=date(2026, 10, 1)
    )
    assert applies is True
    assert "custom" in reason


def test_evaluate_unknown_type(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, rule_type="weekend", conditions={"days_of_week": [5]})
    r.rule_type = "bogus"  # bypass constructor validation for test
    applies, reason = pricing_rules.evaluate_rule(
        r, service=None, check_in=date(2026, 10, 3), today=date(2026, 10, 1)
    )
    assert applies is False
    assert "unsupported" in reason


# ---------- compute_adjusted_price ----------


def test_compute_percent_positive(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, action={"type": "percent", "value": 15})
    new, delta, pct = pricing_rules.compute_adjusted_price(Decimal("500.00"), r)
    assert str(new) == "575.00"
    assert str(delta) == "75.00"
    assert str(pct) == "15.00"


def test_compute_percent_negative(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, action={"type": "percent", "value": -20})
    new, delta, pct = pricing_rules.compute_adjusted_price(Decimal("500.00"), r)
    assert str(new) == "400.00"
    assert str(delta) == "-100.00"
    assert str(pct) == "-20.00"


def test_compute_fixed_positive(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, action={"type": "fixed", "value": 50})
    new, delta, _ = pricing_rules.compute_adjusted_price(Decimal("500.00"), r)
    assert str(new) == "550.00"
    assert str(delta) == "50.00"


def test_compute_fixed_negative(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, action={"type": "fixed", "value": -30})
    new, delta, _ = pricing_rules.compute_adjusted_price(Decimal("500.00"), r)
    assert str(new) == "470.00"
    assert str(delta) == "-30.00"


def test_compute_floor_at_zero(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, action={"type": "fixed", "value": -1000})
    new, delta, _ = pricing_rules.compute_adjusted_price(Decimal("500.00"), r)
    assert str(new) == "0.00"
    assert str(delta) == "-500.00"


def test_compute_bad_action_type(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, action={"type": "bogus", "value": 10})
    with pytest.raises(ValueError):
        pricing_rules.compute_adjusted_price(Decimal("500.00"), r)


# ---------- preview_price ----------


def test_preview_no_rules(db: Session, sample_tenant: Tenant) -> None:
    s = _svc(db, sample_tenant, price=500)
    out = pricing_rules.preview_price(
        db, tenant_id=sample_tenant.id, service=s, check_in=date(2026, 10, 3)
    )
    assert out["original_price"] == "500.00"
    assert out["final_price"] == "500.00"
    assert out["applied_rules"] == []


def test_preview_single_weekend_rule(db: Session, sample_tenant: Tenant) -> None:
    s = _svc(db, sample_tenant, price=500)
    _rule(
        db, sample_tenant, rule_type="weekend",
        conditions={"days_of_week": [5, 6]},
        action={"type": "percent", "value": 20},
    )
    out = pricing_rules.preview_price(
        db, tenant_id=sample_tenant.id, service=s, check_in=date(2026, 10, 3),
        today=date(2026, 10, 1),
    )
    assert out["original_price"] == "500.00"
    assert out["final_price"] == "600.00"
    assert len(out["applied_rules"]) == 1
    assert out["applied_rules"][0]["rule_type"] == "weekend"


def test_preview_stacking_multiple_rules(db: Session, sample_tenant: Tenant) -> None:
    s = _svc(db, sample_tenant, price=500)
    # Priority 50: +10%
    _rule(db, sample_tenant, name="base", rule_type="custom", priority=50,
          action={"type": "percent", "value": 10})
    # Priority 100: -50 AED
    _rule(db, sample_tenant, name="off", rule_type="custom", priority=100,
          action={"type": "fixed", "value": -50})

    out = pricing_rules.preview_price(
        db, tenant_id=sample_tenant.id, service=s, check_in=date(2026, 10, 3),
        today=date(2026, 10, 1),
    )
    # 500 -> +10% = 550 -> -50 = 500
    assert out["final_price"] == "500.00"
    assert [r["name"] for r in out["applied_rules"]] == ["base", "off"]


def test_preview_service_filter(db: Session, sample_tenant: Tenant) -> None:
    a = _svc(db, sample_tenant, name="A", price=500)
    b = _svc(db, sample_tenant, name="B", price=500)
    _rule(
        db, sample_tenant, rule_type="custom",
        action={"type": "percent", "value": 25},
        service_ids=[a.id],
    )
    out_a = pricing_rules.preview_price(
        db, tenant_id=sample_tenant.id, service=a, check_in=date(2026, 10, 3),
        today=date(2026, 10, 1),
    )
    out_b = pricing_rules.preview_price(
        db, tenant_id=sample_tenant.id, service=b, check_in=date(2026, 10, 3),
        today=date(2026, 10, 1),
    )
    assert out_a["final_price"] == "625.00"
    assert out_b["final_price"] == "500.00"


def test_preview_valid_from_to_filter(db: Session, sample_tenant: Tenant) -> None:
    s = _svc(db, sample_tenant, price=500)
    _rule(
        db, sample_tenant, rule_type="custom",
        action={"type": "percent", "value": 50},
        valid_from=date(2026, 12, 1),
        valid_to=date(2026, 12, 31),
    )
    # today before range -> rule ignored
    out = pricing_rules.preview_price(
        db, tenant_id=sample_tenant.id, service=s, check_in=date(2026, 10, 3),
        today=date(2026, 10, 1),
    )
    assert out["final_price"] == "500.00"

    # today inside range -> rule applies
    out = pricing_rules.preview_price(
        db, tenant_id=sample_tenant.id, service=s, check_in=date(2026, 12, 15),
        today=date(2026, 12, 10),
    )
    assert out["final_price"] == "750.00"


def test_preview_inactive_rule_ignored(db: Session, sample_tenant: Tenant) -> None:
    s = _svc(db, sample_tenant, price=500)
    _rule(db, sample_tenant, rule_type="custom", active=False,
          action={"type": "percent", "value": 50})
    out = pricing_rules.preview_price(
        db, tenant_id=sample_tenant.id, service=s, check_in=date(2026, 10, 3),
        today=date(2026, 10, 1),
    )
    assert out["final_price"] == "500.00"


# ---------- record_application ----------


def test_record_application_persists(db: Session, sample_tenant: Tenant) -> None:
    r = _rule(db, sample_tenant, rule_type="custom",
              action={"type": "percent", "value": 10})
    app = pricing_rules.record_application(
        db,
        tenant_id=sample_tenant.id,
        rule_id=r.id,
        original_price=Decimal("500.00"),
        adjusted_price=Decimal("550.00"),
        delta_amount=Decimal("50.00"),
        delta_percent=Decimal("10.00"),
        currency="AED",
        service_id=None,
        booking_id=None,
        note="unit test",
    )
    assert app.id
    assert app.original_price == "500.00"
    assert app.adjusted_price == "550.00"
    assert app.delta_amount == "50.00"
    assert app.delta_percent == "10.00"

    # verify persisted
    row = db.query(PricingRuleApplication).filter(PricingRuleApplication.id == app.id).one()
    assert row.note == "unit test"
