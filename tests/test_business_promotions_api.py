"""Tests for business promotions API (Phase 38, Step 3)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User


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


def _login(client, slug, email="owner@biz.test"):
    r = client.post("/business/api/auth/login",
                    json={"email": email, "password": "OwnerPass123"},
                    headers={"X-Tenant-Slug": slug})
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Tenant-Slug": slug}


def test_requires_auth(client, db):
    t = _tenant(db, "pm-noauth")
    r = client.get("/business/api/promotions", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_crud(client, db):
    t = _tenant(db, "pm-crud")
    _biz(db, t)
    h = _login(client, t.slug)
    assert client.get("/business/api/promotions", headers=h).json()["total"] == 0
    r = client.post("/business/api/promotions",
                    json={"code": "SUMMER20", "name": "Summer 20",
                          "discount_type": "percent", "discount_value": 20},
                    headers=h)
    assert r.status_code == 200
    pid = r.json()["id"]
    assert r.json()["code"] == "summer20"
    r = client.patch(f"/business/api/promotions/{pid}",
                     json={"discount_value": 25}, headers=h)
    assert r.status_code == 200
    r = client.delete(f"/business/api/promotions/{pid}", headers=h)
    assert r.status_code == 200
    assert r.json()["active"] is False


def test_staff_forbidden(client, db):
    t = _tenant(db, "pm-staff")
    _biz(db, t, email="staff@biz.test", role="staff")
    h = _login(client, t.slug, "staff@biz.test")
    r = client.post("/business/api/promotions",
                    json={"code": "x", "name": "X", "discount_value": 10},
                    headers=h)
    assert r.status_code == 403


def test_duplicate_code_400(client, db):
    t = _tenant(db, "pm-dup")
    _biz(db, t)
    h = _login(client, t.slug)
    client.post("/business/api/promotions",
                json={"code": "x", "name": "X", "discount_value": 10}, headers=h)
    r = client.post("/business/api/promotions",
                    json={"code": "x", "name": "Y", "discount_value": 10}, headers=h)
    assert r.status_code == 400


def test_validate_ok(client, db):
    t = _tenant(db, "pm-val")
    _biz(db, t)
    h = _login(client, t.slug)
    client.post("/business/api/promotions",
                json={"code": "SAVE10", "name": "Save 10", "discount_value": 10}, headers=h)
    r = client.post("/business/api/promotions/validate",
                    json={"code": "SAVE10", "amount": 500}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["discount_amount"] == "50.00"
    assert body["new_amount"] == "450.00"


def test_validate_not_found(client, db):
    t = _tenant(db, "pm-valnf")
    _biz(db, t)
    h = _login(client, t.slug)
    r = client.post("/business/api/promotions/validate",
                    json={"code": "NOPE", "amount": 500}, headers=h)
    assert r.json()["valid"] is False
