"""Tests for Promotion model (Phase 38, Step 1)."""
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.promotion import Promotion
from app.models.tenant import Tenant


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def test_create_promotion(db):
    t = _tenant(db, "prom-create")
    p = Promotion(tenant_id=t.id, code="summer20", name="Summer 20%",
                  discount_type="percent", discount_value=Decimal("20"),
                  active=True)
    db.add(p); db.commit(); db.refresh(p)
    assert p.id
    assert p.code == "summer20"
    assert p.used_count == 0
    assert p.max_uses_per_user == 1
    assert p.service_ids == []


def test_unique_code_per_tenant(db):
    t = _tenant(db, "prom-uniq")
    db.add(Promotion(tenant_id=t.id, code="x10", name="A"))
    db.commit()
    db.add(Promotion(tenant_id=t.id, code="x10", name="B"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_same_code_different_tenants(db):
    t1 = _tenant(db, "prom-a")
    t2 = _tenant(db, "prom-b")
    db.add(Promotion(tenant_id=t1.id, code="x10", name="A"))
    db.add(Promotion(tenant_id=t2.id, code="x10", name="B"))
    db.commit()
    assert db.query(Promotion).count() == 2


def test_defaults(db):
    t = _tenant(db, "prom-def")
    p = Promotion(tenant_id=t.id, code="y10", name="Y")
    db.add(p); db.commit(); db.refresh(p)
    assert p.discount_type == "percent"
    assert p.active is True
    assert p.used_count == 0
    assert p.max_uses is None
    assert p.max_uses_per_user == 1


def test_service_ids_and_dates(db):
    t = _tenant(db, "prom-svc")
    p = Promotion(
        tenant_id=t.id, code="spring15", name="Spring",
        discount_type="percent", discount_value=Decimal("15"),
        service_ids=["svc-1", "svc-2"],
        valid_from=date(2026, 10, 1), valid_to=date(2026, 12, 31),
    )
    db.add(p); db.commit(); db.refresh(p)
    assert p.service_ids == ["svc-1", "svc-2"]
    assert p.valid_from == date(2026, 10, 1)
