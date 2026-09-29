"""Tests for booking modification service (Phase 35, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import booking_mod_service


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="u@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="U", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, t, name="R", price=500, capacity=2):
    s = Service(tenant_id=t.id, type="room", name=name,
                price=Decimal(str(price)), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _bk(db, t, u, svc, *, offset=10, nights=2, amount=1000, status="confirmed", service_id=True):
    ci = date.today() + timedelta(days=offset)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=(svc.id if service_id else None),
                service_name=(svc.name if svc else "R"),
                check_in=ci, check_out=ci + timedelta(days=nights),
                guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_can_modify_ok(db):
    t = _tenant(db, "mod-ok")
    u = _user(db, t)
    s = _svc(db, t)
    b = _bk(db, t, u, s, offset=10)
    ok, reason = booking_mod_service.can_modify(b)
    assert ok is True


def test_can_modify_past_checkin(db):
    t = _tenant(db, "mod-past")
    u = _user(db, t)
    s = _svc(db, t)
    b = _bk(db, t, u, s, offset=-1)
    ok, reason = booking_mod_service.can_modify(b)
    assert ok is False


def test_can_modify_cancelled(db):
    t = _tenant(db, "mod-cxl")
    u = _user(db, t)
    s = _svc(db, t)
    b = _bk(db, t, u, s, status="cancelled")
    ok, reason = booking_mod_service.can_modify(b)
    assert ok is False


def test_modify_changes_dates(db):
    t = _tenant(db, "mod-dates")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    b = _bk(db, t, u, s, offset=10, nights=2, amount=1000)
    new_ci = date.today() + timedelta(days=20)
    new_co = new_ci + timedelta(days=3)
    out = booking_mod_service.modify_booking(db, booking=b, new_check_in=new_ci, new_check_out=new_co)
    assert out["ok"] is True
    db.refresh(b)
    assert b.check_in == new_ci
    assert b.check_out == new_co
    # 3 nights * 500 = 1500, delta = +500
    assert out["delta_amount"] == "500.00"
    assert out["new_total"] == "1500.00"


def test_modify_rejects_bad_dates(db):
    t = _tenant(db, "mod-bad")
    u = _user(db, t)
    s = _svc(db, t)
    b = _bk(db, t, u, s, offset=10)
    with pytest.raises(ValueError):
        booking_mod_service.modify_booking(
            db, booking=b,
            new_check_in=date.today() + timedelta(days=5),
            new_check_out=date.today() + timedelta(days=4),
        )


def test_modify_rejects_past(db):
    t = _tenant(db, "mod-past2")
    u = _user(db, t)
    s = _svc(db, t)
    b = _bk(db, t, u, s, offset=10)
    with pytest.raises(ValueError):
        booking_mod_service.modify_booking(
            db, booking=b,
            new_check_in=date.today() - timedelta(days=1),
            new_check_out=date.today() + timedelta(days=1),
        )


def test_modify_detects_overlap(db):
    t = _tenant(db, "mod-overlap")
    u = _user(db, t)
    s = _svc(db, t, capacity=1)
    b1 = _bk(db, t, u, s, offset=10, nights=3)
    # another active booking on same service
    b2 = _bk(db, t, u, s, offset=20, nights=3)
    # try to move b1 to overlap b2's window
    new_ci = date.today() + timedelta(days=21)
    new_co = new_ci + timedelta(days=2)
    out = booking_mod_service.modify_booking(db, booking=b1, new_check_in=new_ci, new_check_out=new_co)
    assert out["ok"] is False
    assert "overlap" in out["reason"].lower()


def test_modify_no_service_keeps_amount(db):
    t = _tenant(db, "mod-nosvc")
    u = _user(db, t)
    s = _svc(db, t)
    # create booking without service_id
    b = _bk(db, t, u, s, offset=10, nights=2, amount=1000, service_id=False)
    new_ci = date.today() + timedelta(days=15)
    new_co = new_ci + timedelta(days=4)
    out = booking_mod_service.modify_booking(db, booking=b, new_check_in=new_ci, new_check_out=new_co)
    assert out["ok"] is True
    # Amount unchanged because no service
    assert out["delta_amount"] == "0.00"
    assert out["new_total"] == "1000.00"


def test_modify_writes_note(db):
    t = _tenant(db, "mod-note")
    u = _user(db, t)
    s = _svc(db, t)
    b = _bk(db, t, u, s, offset=10)
    new_ci = date.today() + timedelta(days=20)
    new_co = new_ci + timedelta(days=1)
    booking_mod_service.modify_booking(db, booking=b, new_check_in=new_ci, new_check_out=new_co)
    db.refresh(b)
    assert "modified" in (b.notes or "").lower()
    assert "delta=" in (b.notes or "")
