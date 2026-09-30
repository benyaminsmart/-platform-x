"""Tests for recent searches API (Phase 42, Step 1)."""
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password, create_access_token
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


def _h(u, t):
    tok = create_access_token(u.id, tenant_id=t.id)
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug}


def test_requires_auth(client, db):
    t = _tenant(db, "rs-noauth")
    r = client.get("/me/recent-searches", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_list_empty(client, db):
    t = _tenant(db, "rs-empty")
    u = _user(db, t)
    r = client.get("/me/recent-searches", headers=_h(u, t))
    assert r.status_code == 200
    assert r.json() == []


def test_save_and_list(client, db):
    t = _tenant(db, "rs-save")
    u = _user(db, t)
    h = _h(u, t)
    ci = (date.today() + timedelta(days=10)).isoformat()
    co = (date.today() + timedelta(days=12)).isoformat()
    r = client.post("/me/recent-searches",
                    json={"check_in": ci, "check_out": co, "guests": 2, "category": "hotels"},
                    headers=h)
    assert r.status_code == 201
    r2 = client.get("/me/recent-searches", headers=h)
    assert len(r2.json()) == 1
    assert r2.json()[0]["category"] == "hotels"


def test_save_empty_ignored(client, db):
    t = _tenant(db, "rs-ignored")
    u = _user(db, t)
    h = _h(u, t)
    r = client.post("/me/recent-searches", json={"guests": 1}, headers=h)
    assert r.status_code == 201
    assert r.json() is None


def test_clear(client, db):
    t = _tenant(db, "rs-clear")
    u = _user(db, t)
    h = _h(u, t)
    ci = (date.today() + timedelta(days=10)).isoformat()
    client.post("/me/recent-searches", json={"check_in": ci, "category": "hotels"}, headers=h)
    r = client.delete("/me/recent-searches", headers=h)
    assert r.json()["deleted"] == 1


def test_prune_keeps_last_10(client, db):
    t = _tenant(db, "rs-prune")
    u = _user(db, t)
    h = _h(u, t)
    for i in range(15):
        ci = (date.today() + timedelta(days=i + 1)).isoformat()
        client.post("/me/recent-searches", json={"check_in": ci, "category": "hotels"}, headers=h)
    r = client.get("/me/recent-searches", headers=h)
    assert len(r.json()) == 10
