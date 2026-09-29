"""Tests for rooms service + API (Phase 36, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import room_service


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _biz(db, t, email="owner@biz.test", role="owner"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("OwnerPass123"),
             first_name="O", last_name="X", business_role=role, status="active",
             referral_code=email[:10].upper())
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name="R",
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _guest(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _login(client, slug, email="owner@biz.test"):
    r = client.post("/business/api/auth/login",
                    json={"email": email, "password": "OwnerPass123"},
                    headers={"X-Tenant-Slug": slug})
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Tenant-Slug": slug}


def test_create_room(db):
    t = _tenant(db, "rm-s")
    r = room_service.create_room(db, t, number="101", floor=1, type="deluxe")
    assert r.id


def test_create_duplicate_number(db):
    t = _tenant(db, "rm-s2")
    room_service.create_room(db, t, number="101")
    try:
        room_service.create_room(db, t, number="101")
        assert False
    except ValueError:
        pass


def test_create_invalid_status(db):
    t = _tenant(db, "rm-s3")
    try:
        room_service.create_room(db, t, number="101", status="bogus")
        assert False
    except ValueError:
        pass


def test_find_available_room(db):
    t = _tenant(db, "rm-find")
    s = _svc(db, t)
    room_service.create_room(db, t, number="101", service_id=s.id)
    room_service.create_room(db, t, number="102", service_id=s.id)
    u = _guest(db, t)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=s.id, service_name=s.name,
                check_in=date.today() + timedelta(days=10),
                check_out=date.today() + timedelta(days=12),
                guests=1, amount=Decimal("1000"), discount=Decimal("0"),
                total_amount=Decimal("1000"), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    room = room_service.find_available_room_for_booking(db, tenant=t, booking=b)
    assert room is not None


def test_assign_room_ok(db):
    t = _tenant(db, "rm-assign")
    s = _svc(db, t)
    room_service.create_room(db, t, number="101", service_id=s.id)
    u = _guest(db, t)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=s.id, service_name=s.name,
                check_in=date.today() + timedelta(days=10),
                check_out=date.today() + timedelta(days=12),
                guests=1, amount=Decimal("1000"), discount=Decimal("0"),
                total_amount=Decimal("1000"), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    out = room_service.assign_room_to_booking(db, tenant=t, booking=b)
    assert out["ok"] is True
    assert out["room_number"] == "101"


def test_assign_avoids_conflict(db):
    t = _tenant(db, "rm-conf")
    s = _svc(db, t)
    room_service.create_room(db, t, number="101", service_id=s.id)
    room_service.create_room(db, t, number="102", service_id=s.id)
    u = _guest(db, t)
    b1 = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                 service_id=s.id, service_name=s.name, room_number="101",
                 check_in=date.today() + timedelta(days=10),
                 check_out=date.today() + timedelta(days=12),
                 guests=1, amount=Decimal("1000"), discount=Decimal("0"),
                 total_amount=Decimal("1000"), currency="AED",
                 status="confirmed", payment_status="paid")
    db.add(b1); db.commit()
    b2 = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                 service_id=s.id, service_name=s.name,
                 check_in=date.today() + timedelta(days=10),
                 check_out=date.today() + timedelta(days=11),
                 guests=1, amount=Decimal("500"), discount=Decimal("0"),
                 total_amount=Decimal("500"), currency="AED",
                 status="confirmed", payment_status="paid")
    db.add(b2); db.commit(); db.refresh(b2)
    room = room_service.find_available_room_for_booking(db, tenant=t, booking=b2)
    assert room is not None
    assert room.number == "102"


def test_api_requires_auth(client, db):
    t = _tenant(db, "rmapi-noauth")
    r = client.get("/business/api/rooms", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_api_crud(client, db):
    t = _tenant(db, "rmapi-crud")
    _biz(db, t)
    h = _login(client, t.slug)
    assert client.get("/business/api/rooms", headers=h).json()["total"] == 0
    r = client.post("/business/api/rooms",
                    json={"number": "101", "floor": 1, "type": "deluxe"}, headers=h)
    assert r.status_code == 200
    rid = r.json()["id"]
    r = client.patch(f"/business/api/rooms/{rid}",
                     json={"status": "maintenance"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "maintenance"
    assert client.get("/business/api/rooms", headers=h).json()["total"] == 1
    r = client.delete(f"/business/api/rooms/{rid}", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "inactive"


def test_api_staff_forbidden(client, db):
    t = _tenant(db, "rmapi-staff")
    _biz(db, t, email="staff@biz.test", role="staff")
    h = _login(client, t.slug, "staff@biz.test")
    r = client.post("/business/api/rooms", json={"number": "101"}, headers=h)
    assert r.status_code == 403


def test_api_duplicate_400(client, db):
    t = _tenant(db, "rmapi-dup")
    _biz(db, t)
    h = _login(client, t.slug)
    client.post("/business/api/rooms", json={"number": "101"}, headers=h)
    r = client.post("/business/api/rooms", json={"number": "101"}, headers=h)
    assert r.status_code == 400
