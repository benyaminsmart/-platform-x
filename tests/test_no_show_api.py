"""Tests for no-show service + API (Phase 35, Step 4)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services import no_show_service


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


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _bk(db, t, u, *, offset=-3, status="confirmed", paid=True):
    ci = date.today() + timedelta(days=offset)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
                guests=1, amount=Decimal("500"), discount=Decimal("0"),
                total_amount=Decimal("500"), currency="AED",
                status=status, payment_status=("paid" if paid else "pending"))
    db.add(b); db.commit(); db.refresh(b)
    return b


def _login(client, slug, email="owner@biz.test"):
    r = client.post("/business/api/auth/login",
                    json={"email": email, "password": "OwnerPass123"},
                    headers={"X-Tenant-Slug": slug})
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Tenant-Slug": slug}


def test_candidate_past_confirmed(db):
    t = _tenant(db, "ns-cand")
    u = _user(db, t)
    b = _bk(db, t, u, offset=-3, status="confirmed")
    assert no_show_service.is_no_show_candidate(b) is True


def test_not_candidate_future(db):
    t = _tenant(db, "ns-future")
    u = _user(db, t)
    b = _bk(db, t, u, offset=5, status="confirmed")
    assert no_show_service.is_no_show_candidate(b) is False


def test_not_candidate_checked_in(db):
    t = _tenant(db, "ns-ci")
    u = _user(db, t)
    b = _bk(db, t, u, offset=-3, status="checked_in")
    assert no_show_service.is_no_show_candidate(b) is False


def test_mark_no_show(db):
    t = _tenant(db, "ns-mark")
    u = _user(db, t)
    b = _bk(db, t, u, offset=-3)
    out = no_show_service.mark_no_show(db, booking=b)
    assert out["ok"] is True
    db.refresh(b)
    assert b.status == "no_show"


def test_mark_no_show_ineligible(db):
    t = _tenant(db, "ns-bad")
    u = _user(db, t)
    b = _bk(db, t, u, offset=5)
    out = no_show_service.mark_no_show(db, booking=b)
    assert out["ok"] is False


def test_api_list_requires_auth(client, db):
    t = _tenant(db, "nsapi-noauth")
    r = client.get("/business/api/no-shows", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_api_list_candidates(client, db):
    t = _tenant(db, "nsapi-list")
    _biz(db, t)
    u = _user(db, t)
    _bk(db, t, u, offset=-3)
    _bk(db, t, u, offset=-5)
    _bk(db, t, u, offset=5)
    h = _login(client, t.slug)
    r = client.get("/business/api/no-shows", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2


def test_api_mark_ok(client, db):
    t = _tenant(db, "nsapi-mark")
    _biz(db, t)
    u = _user(db, t)
    b = _bk(db, t, u, offset=-3)
    h = _login(client, t.slug)
    r = client.post(f"/business/api/no-shows/{b.id}/mark", headers=h)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_api_mark_staff_forbidden(client, db):
    t = _tenant(db, "nsapi-staff")
    _biz(db, t, email="staff@biz.test", role="staff")
    u = _user(db, t, "g2@x.com")
    b = _bk(db, t, u, offset=-3)
    h = _login(client, t.slug, "staff@biz.test")
    r = client.post(f"/business/api/no-shows/{b.id}/mark", headers=h)
    assert r.status_code == 403


def test_api_cross_tenant_blocked(client, db):
    a = _tenant(db, "nsapi-a")
    b = _tenant(db, "nsapi-b")
    _biz(db, a)
    ub = _user(db, b, "gb@x.com")
    bb = _bk(db, b, ub, offset=-3)
    h = _login(client, a.slug)
    r = client.post(f"/business/api/no-shows/{bb.id}/mark", headers=h)
    assert r.status_code == 404
