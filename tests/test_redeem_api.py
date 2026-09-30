"""Tests for redeem API (Phase 44, Step 2)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password, create_access_token
from app.models.redeem_option import RedeemOption
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, points=0, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(),
             status="active", points=points)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _option(db, name="25 AED credit", cost=500, value=25):
    o = RedeemOption(name=name, description="test",
                     points_cost=cost, reward_type="credit",
                     reward_value=Decimal(str(value)), active=True, display_order=10)
    db.add(o); db.commit(); db.refresh(o)
    return o


def _h(u, t):
    tok = create_access_token(u.id, tenant_id=t.id)
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug}


def test_list_options(client, db):
    _option(db)
    r = client.get("/rewards/redeem-options")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_redeem_requires_auth(client, db):
    o = _option(db)
    r = client.post(f"/rewards/redeem-options/{o.id}/redeem",
                    headers={"X-Tenant-Slug": "x"})
    assert r.status_code == 401


def test_redeem_not_enough_points(client, db):
    t = _tenant(db, "rd-notenough")
    u = _user(db, t, points=100)
    o = _option(db)
    h = _h(u, t)
    r = client.post(f"/rewards/redeem-options/{o.id}/redeem", headers=h)
    assert r.status_code == 400
    assert "not enough" in r.json()["detail"].lower()


def test_redeem_ok(client, db):
    t = _tenant(db, "rd-ok")
    u = _user(db, t, points=1000)
    o = _option(db)
    h = _h(u, t)
    r = client.post(f"/rewards/redeem-options/{o.id}/redeem", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["points_spent"] == 500
    db.refresh(u)
    assert u.points == 500


def test_redeem_unknown_option(client, db):
    t = _tenant(db, "rd-unknown")
    u = _user(db, t, points=1000)
    h = _h(u, t)
    r = client.post("/rewards/redeem-options/bogus/redeem", headers=h)
    assert r.status_code == 400
