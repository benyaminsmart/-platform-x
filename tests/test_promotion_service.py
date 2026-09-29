"""Tests for promotion service (Phase 38, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.services import promotion_service as svc


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def test_create_ok(db):
    t = _tenant(db, "ps-create")
    p = svc.create_promotion(db, t, code="SUMMER20", name="Summer",
                             discount_type="percent", discount_value=20)
    assert p.code == "summer20"


def test_create_duplicate_code(db):
    t = _tenant(db, "ps-dup")
    svc.create_promotion(db, t, code="x", name="X", discount_value=10)
    try:
        svc.create_promotion(db, t, code="x", name="Y", discount_value=10)
        assert False
    except ValueError:
        pass


def test_create_invalid_type(db):
    t = _tenant(db, "ps-badtype")
    try:
        svc.create_promotion(db, t, code="x", name="X", discount_type="bogus", discount_value=10)
        assert False
    except ValueError:
        pass


def test_create_zero_value(db):
    t = _tenant(db, "ps-zeroval")
    try:
        svc.create_promotion(db, t, code="x", name="X", discount_value=0)
        assert False
    except ValueError:
        pass


def test_validate_ok(db):
    t = _tenant(db, "pv-ok")
    svc.create_promotion(db, t, code="save10", name="Save", discount_value=10)
    p, reason = svc.validate_promotion(db, tenant=t, code="save10", base_amount=500)
    assert p is not None
    assert reason == "ok"


def test_validate_not_found(db):
    t = _tenant(db, "pv-nf")
    p, reason = svc.validate_promotion(db, tenant=t, code="missing", base_amount=500)
    assert p is None


def test_validate_inactive(db):
    t = _tenant(db, "pv-inactive")
    p = svc.create_promotion(db, t, code="x", name="X", discount_value=10)
    svc.delete_promotion(db, t, p.id)
    pr, reason = svc.validate_promotion(db, tenant=t, code="x", base_amount=500)
    assert pr is None


def test_validate_expired(db):
    t = _tenant(db, "pv-exp")
    svc.create_promotion(db, t, code="old", name="Old", discount_value=10,
                         valid_to=date.today() - timedelta(days=1))
    pr, reason = svc.validate_promotion(db, tenant=t, code="old", base_amount=500)
    assert pr is None
    assert "expired" in reason


def test_validate_not_yet(db):
    t = _tenant(db, "pv-future")
    svc.create_promotion(db, t, code="future", name="Future", discount_value=10,
                         valid_from=date.today() + timedelta(days=10))
    pr, reason = svc.validate_promotion(db, tenant=t, code="future", base_amount=500)
    assert pr is None
    assert "not yet" in reason


def test_validate_min_amount(db):
    t = _tenant(db, "pv-min")
    svc.create_promotion(db, t, code="big", name="Big", discount_value=10, min_amount=1000)
    pr, reason = svc.validate_promotion(db, tenant=t, code="big", base_amount=500)
    assert pr is None
    pr, reason = svc.validate_promotion(db, tenant=t, code="big", base_amount=1500)
    assert pr is not None


def test_validate_max_uses(db):
    t = _tenant(db, "pv-max")
    p = svc.create_promotion(db, t, code="capped", name="Capped", discount_value=10, max_uses=2)
    p.used_count = 2
    db.commit()
    pr, reason = svc.validate_promotion(db, tenant=t, code="capped", base_amount=500)
    assert pr is None


def test_validate_service_restriction(db):
    t = _tenant(db, "pv-svc")
    svc.create_promotion(db, t, code="onlyA", name="Only A", discount_value=10,
                         service_ids=["A"])
    pr, reason = svc.validate_promotion(db, tenant=t, code="onlyA", base_amount=500, service_id="B")
    assert pr is None
    pr2, _ = svc.validate_promotion(db, tenant=t, code="onlyA", base_amount=500, service_id="A")
    assert pr2 is not None


def test_apply_percent(db):
    t = _tenant(db, "pa-pct")
    p = svc.create_promotion(db, t, code="x", name="X", discount_type="percent", discount_value=20)
    new_amount, disc = svc.apply_promotion(Decimal("500"), p)
    assert str(new_amount) == "400.00"
    assert str(disc) == "100.00"


def test_apply_fixed(db):
    t = _tenant(db, "pa-fix")
    p = svc.create_promotion(db, t, code="x", name="X", discount_type="fixed", discount_value=50)
    new_amount, disc = svc.apply_promotion(Decimal("500"), p)
    assert str(new_amount) == "450.00"
    assert str(disc) == "50.00"


def test_apply_floors_at_zero(db):
    t = _tenant(db, "pa-floor")
    p = svc.create_promotion(db, t, code="x", name="X", discount_type="fixed", discount_value=9999)
    new_amount, disc = svc.apply_promotion(Decimal("500"), p)
    assert str(new_amount) == "0.00"
    assert str(disc) == "500.00"


def test_increment_usage(db):
    t = _tenant(db, "pi-inc")
    p = svc.create_promotion(db, t, code="x", name="X", discount_value=10)
    assert p.used_count == 0
    svc.increment_usage(db, p)
    svc.increment_usage(db, p)
    assert p.used_count == 2
