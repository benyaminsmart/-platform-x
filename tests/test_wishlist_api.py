"""Tests for Wishlist API (Phase 33, Step 2)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.service import Service
from app.models.tenant import Tenant
from app.core.security import create_access_token, hash_password
from app.models.user import User


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, tenant, email):
    u = User(tenant_id=tenant.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="U", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, tenant, name="R"):
    s = Service(tenant_id=tenant.id, type="room", name=name,
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _h(user, tenant):
    tok = create_access_token(user.id, tenant_id=tenant.id)
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": tenant.slug}


def test_requires_auth(client, db):
    t = _tenant(db, "wl-noauth")
    r = client.get("/wishlist", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_empty_list(client, db):
    t = _tenant(db, "wl-empty")
    u = _user(db, t, "e@x.com")
    r = client.get("/wishlist", headers=_h(u, t))
    assert r.status_code == 200
    assert r.json() == []


def test_add_and_list(client, db):
    t = _tenant(db, "wl-add")
    u = _user(db, t, "a@x.com")
    s = _svc(db, t, "Deluxe")
    h = _h(u, t)
    r = client.post("/wishlist", json={"service_id": s.id, "note": "Future"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    listing = client.get("/wishlist", headers=h).json()
    assert len(listing) == 1
    assert listing[0]["service_name"] == "Deluxe"
    assert listing[0]["note"] == "Future"


def test_add_idempotent(client, db):
    t = _tenant(db, "wl-idem")
    u = _user(db, t, "i@x.com")
    s = _svc(db, t, "R")
    h = _h(u, t)
    r1 = client.post("/wishlist", json={"service_id": s.id}, headers=h)
    r2 = client.post("/wishlist", json={"service_id": s.id}, headers=h)
    assert r1.json()["status"] == "ok"
    assert r2.json()["status"] == "already"


def test_add_not_found(client, db):
    t = _tenant(db, "wl-nf")
    u = _user(db, t, "nf@x.com")
    r = client.post("/wishlist", json={"service_id": "bogus"}, headers=_h(u, t))
    assert r.status_code == 404


def test_remove(client, db):
    t = _tenant(db, "wl-rm")
    u = _user(db, t, "r@x.com")
    s = _svc(db, t, "R")
    h = _h(u, t)
    client.post("/wishlist", json={"service_id": s.id}, headers=h)
    r = client.delete(f"/wishlist/{s.id}", headers=h)
    assert r.status_code == 200
    assert client.get("/wishlist", headers=h).json() == []


def test_remove_not_in_list(client, db):
    t = _tenant(db, "wl-rm-nf")
    u = _user(db, t, "rmnf@x.com")
    r = client.delete("/wishlist/bogus", headers=_h(u, t))
    assert r.status_code == 404


def test_check(client, db):
    t = _tenant(db, "wl-check")
    u = _user(db, t, "c@x.com")
    s = _svc(db, t, "R")
    h = _h(u, t)
    r = client.get(f"/wishlist/check/{s.id}", headers=h)
    assert r.json()["is_wishlisted"] is False
    client.post("/wishlist", json={"service_id": s.id}, headers=h)
    r = client.get(f"/wishlist/check/{s.id}", headers=h)
    assert r.json()["is_wishlisted"] is True


def test_user_isolation(client, db):
    t1 = _tenant(db, "wl-iso1")
    t2 = _tenant(db, "wl-iso2")
    u1 = _user(db, t1, "u1@x.com")
    u2 = _user(db, t2, "u2@x.com")
    s1 = _svc(db, t1, "A")
    s2 = _svc(db, t2, "B")
    client.post("/wishlist", json={"service_id": s1.id}, headers=_h(u1, t1))
    client.post("/wishlist", json={"service_id": s2.id}, headers=_h(u2, t2))
    assert len(client.get("/wishlist", headers=_h(u1, t1)).json()) == 1
    assert len(client.get("/wishlist", headers=_h(u2, t2)).json()) == 1
