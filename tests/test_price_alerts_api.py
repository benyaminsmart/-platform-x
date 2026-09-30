"""Tests for price alerts API (Phase 43, Step 1)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password, create_access_token
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, t, price=500, name="R"):
    s = Service(tenant_id=t.id, type="room", name=name,
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _h(u, t):
    tok = create_access_token(u.id, tenant_id=t.id)
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug}


def test_requires_auth(client, db):
    t = _tenant(db, "pa-noauth")
    r = client.get("/me/price-alerts", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_create_and_list(client, db):
    t = _tenant(db, "pa-crud")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    h = _h(u, t)
    r = client.post("/me/price-alerts",
                    json={"service_id": s.id, "target_price": 400},
                    headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["target_price"] == "400.00"
    r2 = client.get("/me/price-alerts", headers=h)
    assert len(r2.json()) == 1


def test_target_must_be_below_current(client, db):
    t = _tenant(db, "pa-above")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    h = _h(u, t)
    r = client.post("/me/price-alerts",
                    json={"service_id": s.id, "target_price": 600},
                    headers=h)
    assert r.status_code == 400


def test_cannot_have_two_active_alerts_same_service(client, db):
    t = _tenant(db, "pa-dup")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    h = _h(u, t)
    client.post("/me/price-alerts", json={"service_id": s.id, "target_price": 400}, headers=h)
    r = client.post("/me/price-alerts", json={"service_id": s.id, "target_price": 300}, headers=h)
    assert r.status_code == 400


def test_delete(client, db):
    t = _tenant(db, "pa-del")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    h = _h(u, t)
    r = client.post("/me/price-alerts", json={"service_id": s.id, "target_price": 400}, headers=h)
    aid = r.json()["id"]
    r = client.delete(f"/me/price-alerts/{aid}", headers=h)
    assert r.status_code == 200


def test_check_not_triggered(client, db):
    t = _tenant(db, "pa-check1")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    h = _h(u, t)
    client.post("/me/price-alerts", json={"service_id": s.id, "target_price": 400}, headers=h)
    r = client.post("/me/price-alerts/check", headers=h)
    assert r.status_code == 200
    assert r.json()[0]["triggered"] is False


def test_check_triggered(client, db):
    t = _tenant(db, "pa-check2")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    h = _h(u, t)
    client.post("/me/price-alerts", json={"service_id": s.id, "target_price": 400}, headers=h)
    s.price = Decimal("350")
    db.commit()
    r = client.post("/me/price-alerts/check", headers=h)
    assert r.status_code == 200
    assert r.json()[0]["triggered"] is True
    assert r.json()[0]["notified_at"] is not None
