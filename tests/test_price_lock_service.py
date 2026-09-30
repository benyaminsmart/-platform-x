"""Tests for Price Lock service (Phase 47, Step 1)."""
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.price_lock import PriceLock
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import price_lock_service as pls


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, price=500, status="active"):
    s = Service(tenant_id=t.id, type="room", name="Room",
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status=status, display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _user(db, t, email="pl@x.com"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, svc):
    ci = date.today() + timedelta(days=10)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=svc.id, service_name=svc.name,
                check_in=ci, check_out=ci + timedelta(days=1), guests=1,
                amount=Decimal("500"), discount=Decimal("0"),
                total_amount=Decimal("500"), currency="AED",
                status="pending", payment_status="pending")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_create_lock_ok(db):
    t = _tenant(db, "pl-ok")
    s = _svc(db, t, price=500)
    u = _user(db, t)
    lock, status = pls.create_lock(db, user_id=u.id, service_id=s.id)
    assert status == "ok"
    assert lock.locked_price == Decimal("500.00")
    assert lock.currency == "AED"
    assert lock.active is True


def test_create_lock_not_found(db):
    t = _tenant(db, "pl-nf")
    u = _user(db, t, "nf@x.com")
    lock, status = pls.create_lock(db, user_id=u.id, service_id="does-not-exist")
    assert lock is None
    assert status == "not_found"


def test_create_lock_inactive_service(db):
    t = _tenant(db, "pl-inactive")
    s = _svc(db, t, status="inactive")
    u = _user(db, t, "inactive@x.com")
    lock, status = pls.create_lock(db, user_id=u.id, service_id=s.id)
    assert lock is None
    assert status == "not_found"


def test_create_lock_bad_window(db):
    t = _tenant(db, "pl-bw")
    s = _svc(db, t)
    u = _user(db, t, "bw@x.com")
    lock, status = pls.create_lock(db, user_id=u.id, service_id=s.id, window_hours=0)
    assert lock is None
    assert status == "bad_window"
    lock, status = pls.create_lock(db, user_id=u.id, service_id=s.id, window_hours=999)
    assert lock is None
    assert status == "bad_window"


def test_create_replaces_existing(db):
    t = _tenant(db, "pl-replace")
    s = _svc(db, t, price=500)
    u = _user(db, t, "replace@x.com")
    lock1, _ = pls.create_lock(db, user_id=u.id, service_id=s.id)
    s.price = Decimal("800")
    db.commit()
    lock2, status = pls.create_lock(db, user_id=u.id, service_id=s.id)
    assert status == "ok"
    assert lock2.id == lock1.id
    assert lock2.locked_price == Decimal("800.00")


def test_get_active_lock(db):
    t = _tenant(db, "pl-get")
    s = _svc(db, t, price=300)
    u = _user(db, t, "get@x.com")
    pls.create_lock(db, user_id=u.id, service_id=s.id)
    lock = pls.get_active_lock(db, user_id=u.id, service_id=s.id)
    assert lock is not None
    assert lock.locked_price == Decimal("300.00")


def test_get_active_lock_none(db):
    t = _tenant(db, "pl-none")
    s = _svc(db, t)
    u = _user(db, t, "none@x.com")
    assert pls.get_active_lock(db, user_id=u.id, service_id=s.id) is None


def test_list_locks(db):
    t = _tenant(db, "pl-list")
    s1 = _svc(db, t, price=100)
    s2 = _svc(db, t, price=200)
    u = _user(db, t, "list@x.com")
    pls.create_lock(db, user_id=u.id, service_id=s1.id)
    pls.create_lock(db, user_id=u.id, service_id=s2.id)
    rows = pls.list_locks(db, user_id=u.id)
    assert len(rows) == 2
    names = {r["service_name"] for r in rows}
    assert "Room" in names


def test_consume_lock_ok(db):
    t = _tenant(db, "pl-consume")
    s = _svc(db, t, price=500)
    u = _user(db, t, "consume@x.com")
    b = _booking(db, t, u, s)
    pls.create_lock(db, user_id=u.id, service_id=s.id)
    price, status = pls.consume_lock(db, user_id=u.id, service_id=s.id, booking_id=b.id)
    assert status == "ok"
    assert price == Decimal("500.00")
    # Second consume fails
    price2, status2 = pls.consume_lock(db, user_id=u.id, service_id=s.id, booking_id=b.id)
    assert status2 == "not_active"
    assert price2 is None


def test_consume_lock_not_found(db):
    t = _tenant(db, "pl-cnf")
    u = _user(db, t, "cnf@x.com")
    price, status = pls.consume_lock(db, user_id=u.id, service_id="x", booking_id="y")
    assert status == "not_found"


def test_delete_lock(db):
    t = _tenant(db, "pl-del")
    s = _svc(db, t)
    u = _user(db, t, "del@x.com")
    lock, _ = pls.create_lock(db, user_id=u.id, service_id=s.id)
    assert pls.delete_lock(db, user_id=u.id, lock_id=lock.id) is True
    assert pls.delete_lock(db, user_id=u.id, lock_id=lock.id) is False


def test_expired_lock_not_active(db):
    t = _tenant(db, "pl-exp")
    s = _svc(db, t)
    u = _user(db, t, "exp@x.com")
    lock, _ = pls.create_lock(db, user_id=u.id, service_id=s.id)
    # force-expire
    lock.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()
    assert pls.get_active_lock(db, user_id=u.id, service_id=s.id) is None
    price, status = pls.consume_lock(db, user_id=u.id, service_id=s.id, booking_id="x")
    assert status == "not_active"
    assert price is None
