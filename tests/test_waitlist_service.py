"""Tests for Waitlist service (Phase 48, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import waitlist_service as ws


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, price=500, capacity=2, status="active"):
    s = Service(tenant_id=t.id, type="room", name="Room",
                price=Decimal(str(price)), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status=status, display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _user(db, t, email):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, svc, check_in, check_out, status="confirmed"):
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=svc.id, service_name=svc.name,
                check_in=check_in, check_out=check_out, guests=1,
                amount=Decimal("500"), discount=Decimal("0"),
                total_amount=Decimal("500"), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_join_bad_dates(db):
    t = _tenant(db, "wl-bd")
    s = _svc(db, t)
    u = _user(db, t, "bd@x.com")
    ci = date.today() + timedelta(days=10)
    entry, st = ws.join(db, user_id=u.id, service_id=s.id,
                        check_in=ci, check_out=ci)  # same day
    assert st == "bad_dates"
    assert entry is None


def test_join_not_found(db):
    t = _tenant(db, "wl-nf")
    u = _user(db, t, "nf@x.com")
    ci = date.today() + timedelta(days=10)
    entry, st = ws.join(db, user_id=u.id, service_id="x",
                        check_in=ci, check_out=ci + timedelta(days=1))
    assert st == "not_found"


def test_join_not_full(db):
    t = _tenant(db, "wl-full-ok")
    s = _svc(db, t, capacity=5)
    u = _user(db, t, "nf-ok@x.com")
    ci = date.today() + timedelta(days=10)
    entry, st = ws.join(db, user_id=u.id, service_id=s.id,
                        check_in=ci, check_out=ci + timedelta(days=1))
    assert st == "not_full"
    assert entry is None


def test_join_ok(db):
    t = _tenant(db, "wl-ok")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    ci = date.today() + timedelta(days=10)
    co = ci + timedelta(days=2)
    # Fill capacity
    _booking(db, t, u1, s, ci, co)
    # Now full
    entry, st = ws.join(db, user_id=u2.id, service_id=s.id,
                        check_in=ci, check_out=co)
    assert st == "ok"
    assert entry.active is True
    assert entry.position_at_join == 1


def test_join_already(db):
    t = _tenant(db, "wl-already")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "a1@x.com")
    u2 = _user(db, t, "a2@x.com")
    ci = date.today() + timedelta(days=10)
    co = ci + timedelta(days=2)
    _booking(db, t, u1, s, ci, co)
    ws.join(db, user_id=u2.id, service_id=s.id, check_in=ci, check_out=co)
    entry2, st = ws.join(db, user_id=u2.id, service_id=s.id, check_in=ci, check_out=co)
    assert st == "already"


def test_fifo_position_and_notify(db):
    t = _tenant(db, "wl-fifo")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "f1@x.com")
    u2 = _user(db, t, "f2@x.com")
    u3 = _user(db, t, "f3@x.com")
    ci = date.today() + timedelta(days=10)
    co = ci + timedelta(days=2)
    b = _booking(db, t, u1, s, ci, co)

    ws.join(db, user_id=u2.id, service_id=s.id, check_in=ci, check_out=co)
    ws.join(db, user_id=u3.id, service_id=s.id, check_in=ci, check_out=co)

    # Slot is still full
    assert ws.check_and_notify(db, service_id=s.id, check_in=ci, check_out=co) is None

    # Cancel booking → free slot
    b.status = "cancelled"
    db.commit()

    notified = ws.check_and_notify(db, service_id=s.id, check_in=ci, check_out=co)
    assert notified is not None
    assert notified["user_id"] == u2.id  # FIFO first

    # Second call → next user
    notified2 = ws.check_and_notify(db, service_id=s.id, check_in=ci, check_out=co)
    assert notified2 is not None
    assert notified2["user_id"] == u3.id

    # Third call → none (all notified)
    assert ws.check_and_notify(db, service_id=s.id, check_in=ci, check_out=co) is None


def test_list_entries(db):
    t = _tenant(db, "wl-list")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "l1@x.com")
    u2 = _user(db, t, "l2@x.com")
    ci = date.today() + timedelta(days=10)
    co = ci + timedelta(days=2)
    _booking(db, t, u1, s, ci, co)
    ws.join(db, user_id=u2.id, service_id=s.id, check_in=ci, check_out=co)
    rows = ws.list_entries(db, user_id=u2.id)
    assert len(rows) == 1
    assert rows[0]["service_name"] == "Room"
    assert rows[0]["position"] == 1


def test_leave(db):
    t = _tenant(db, "wl-leave")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "lv1@x.com")
    u2 = _user(db, t, "lv2@x.com")
    ci = date.today() + timedelta(days=10)
    co = ci + timedelta(days=2)
    _booking(db, t, u1, s, ci, co)
    entry, _ = ws.join(db, user_id=u2.id, service_id=s.id, check_in=ci, check_out=co)
    assert ws.leave(db, user_id=u2.id, entry_id=entry.id) is True
    assert ws.leave(db, user_id=u2.id, entry_id=entry.id) is False


def test_is_full(db):
    t = _tenant(db, "wl-isfull")
    s = _svc(db, t, capacity=2)
    u1 = _user(db, t, "isf1@x.com")
    ci = date.today() + timedelta(days=10)
    co = ci + timedelta(days=2)
    assert ws.is_full(db, service_id=s.id, check_in=ci, check_out=co) is False
    _booking(db, t, u1, s, ci, co)
    assert ws.is_full(db, service_id=s.id, check_in=ci, check_out=co) is False
    u2 = _user(db, t, "isf2@x.com")
    _booking(db, t, u2, s, ci, co)
    assert ws.is_full(db, service_id=s.id, check_in=ci, check_out=co) is True
