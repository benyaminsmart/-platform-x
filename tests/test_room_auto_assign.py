"""Tests: auto room assignment on payment (Phase 36, Step 4)."""
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.booking import Booking
from app.models.room import Room
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import room_service


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name="R",
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _bk(db, t, u, s, offset=10):
    ci = date.today() + timedelta(days=offset)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=s.id, service_name=s.name,
                check_in=ci, check_out=ci + timedelta(days=2),
                guests=1, amount=Decimal("1000"), discount=Decimal("0"),
                total_amount=Decimal("1000"), currency="AED",
                status="pending", payment_status="pending")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_auto_assign_finds_room(db):
    t = _tenant(db, "auto-a")
    s = _svc(db, t)
    room_service.create_room(db, t, number="101", service_id=s.id)
    room_service.create_room(db, t, number="102", service_id=s.id)
    u = _user(db, t)
    b = _bk(db, t, u, s)
    out = room_service.assign_room_to_booking(db, tenant=t, booking=b)
    assert out["ok"] is True
    db.refresh(b)
    assert b.room_number in ("101", "102")


def test_auto_assign_no_rooms(db):
    t = _tenant(db, "auto-noroom")
    s = _svc(db, t)
    u = _user(db, t)
    b = _bk(db, t, u, s)
    out = room_service.assign_room_to_booking(db, tenant=t, booking=b)
    assert out["ok"] is False


def test_auto_assign_skips_maintenance(db):
    t = _tenant(db, "auto-maint")
    s = _svc(db, t)
    room_service.create_room(db, t, number="101", service_id=s.id, status="maintenance")
    room_service.create_room(db, t, number="102", service_id=s.id, status="available")
    u = _user(db, t)
    b = _bk(db, t, u, s)
    out = room_service.assign_room_to_booking(db, tenant=t, booking=b)
    assert out["ok"] is True
    assert out["room_number"] == "102"
