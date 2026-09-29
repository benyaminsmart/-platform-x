"""Tests for Room model (Phase 36, Step 1)."""
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.room import Room
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


def test_room_create(db):
    t = _tenant(db, "rm-create")
    s = _svc(db, t)
    r = Room(tenant_id=t.id, service_id=s.id, number="101", floor=1, type="deluxe", status="available")
    db.add(r); db.commit(); db.refresh(r)
    assert r.id
    assert r.number == "101"
    assert r.floor == 1


def test_room_unique_number_per_tenant(db):
    t = _tenant(db, "rm-uniq")
    db.add(Room(tenant_id=t.id, number="101"))
    db.commit()
    db.add(Room(tenant_id=t.id, number="101"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_room_same_number_different_tenants(db):
    t1 = _tenant(db, "rm-a")
    t2 = _tenant(db, "rm-b")
    db.add(Room(tenant_id=t1.id, number="101"))
    db.add(Room(tenant_id=t2.id, number="101"))
    db.commit()  # should succeed
    assert db.query(Room).count() == 2


def test_room_default_status(db):
    t = _tenant(db, "rm-status")
    r = Room(tenant_id=t.id, number="202")
    db.add(r); db.commit(); db.refresh(r)
    assert r.status == "available"
