"""Tests for RatePlan model (Phase 37, Step 1)."""
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.rate_plan import RatePlan
from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name="R",
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_create_rate_plan(db):
    t = _tenant(db, "rp-create")
    s = _svc(db, t)
    rp = RatePlan(tenant_id=t.id, service_id=s.id, name="Bed & Breakfast",
                  code="bb", price_modifier_type="percent",
                  price_modifier_value=Decimal("15"), meal_plan="breakfast",
                  refundable=True)
    db.add(rp); db.commit(); db.refresh(rp)
    assert rp.id
    assert rp.code == "bb"
    assert rp.meal_plan == "breakfast"


def test_unique_per_service(db):
    t = _tenant(db, "rp-uniq")
    s = _svc(db, t)
    db.add(RatePlan(tenant_id=t.id, service_id=s.id, name="A", code="bb"))
    db.commit()
    db.add(RatePlan(tenant_id=t.id, service_id=s.id, name="B", code="bb"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_same_code_different_services(db):
    t = _tenant(db, "rp-multi")
    s1 = _svc(db, t)
    s2 = _svc(db, t)
    db.add(RatePlan(tenant_id=t.id, service_id=s1.id, name="A", code="bb"))
    db.add(RatePlan(tenant_id=t.id, service_id=s2.id, name="B", code="bb"))
    db.commit()
    assert db.query(RatePlan).count() == 2


def test_defaults(db):
    t = _tenant(db, "rp-def")
    s = _svc(db, t)
    rp = RatePlan(tenant_id=t.id, service_id=s.id, name="X", code="x")
    db.add(rp); db.commit(); db.refresh(rp)
    assert rp.price_modifier_type == "percent"
    assert rp.meal_plan == "none"
    assert rp.refundable is True
    assert rp.active is True
