"""Tests for rate plan service + API (Phase 37, Step 2)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import rate_plan_service


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name="R",
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


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


def test_create_plan(db):
    t = _tenant(db, "rp-s")
    s = _svc(db, t)
    rp = rate_plan_service.create_plan(db, t, service_id=s.id, name="BB",
                                       code="bb", price_modifier_value=15,
                                       meal_plan="breakfast")
    assert rp.id


def test_create_duplicate_code(db):
    t = _tenant(db, "rp-s2")
    s = _svc(db, t)
    rate_plan_service.create_plan(db, t, service_id=s.id, name="A", code="bb")
    try:
        rate_plan_service.create_plan(db, t, service_id=s.id, name="B", code="bb")
        assert False
    except ValueError:
        pass


def test_create_invalid_meal(db):
    t = _tenant(db, "rp-s3")
    s = _svc(db, t)
    try:
        rate_plan_service.create_plan(db, t, service_id=s.id, name="X", code="x", meal_plan="bogus")
        assert False
    except ValueError:
        pass


def test_create_invalid_service(db):
    t = _tenant(db, "rp-s4")
    try:
        rate_plan_service.create_plan(db, t, service_id="bogus", name="X", code="x")
        assert False
    except ValueError:
        pass


def test_apply_percent(db):
    t = _tenant(db, "rp-apply")
    s = _svc(db, t)
    rp = rate_plan_service.create_plan(db, t, service_id=s.id, name="BB", code="bb",
                                       price_modifier_value=15, price_modifier_type="percent")
    new_price, delta = rate_plan_service.apply_plan_to_price(Decimal("500"), rp)
    assert str(new_price) == "575.00"
    assert str(delta) == "75.00"


def test_apply_fixed(db):
    t = _tenant(db, "rp-fix")
    s = _svc(db, t)
    rp = rate_plan_service.create_plan(db, t, service_id=s.id, name="+50", code="p50",
                                       price_modifier_value=50, price_modifier_type="fixed")
    new_price, delta = rate_plan_service.apply_plan_to_price(Decimal("500"), rp)
    assert str(new_price) == "550.00"


def test_apply_negative(db):
    t = _tenant(db, "rp-neg")
    s = _svc(db, t)
    rp = rate_plan_service.create_plan(db, t, service_id=s.id, name="N", code="n",
                                       price_modifier_value=-20, price_modifier_type="percent")
    new_price, delta = rate_plan_service.apply_plan_to_price(Decimal("500"), rp)
    assert str(new_price) == "400.00"


def test_apply_floor(db):
    t = _tenant(db, "rp-floor")
    s = _svc(db, t)
    rp = rate_plan_service.create_plan(db, t, service_id=s.id, name="X", code="x",
                                       price_modifier_value=-1000, price_modifier_type="fixed")
    new_price, delta = rate_plan_service.apply_plan_to_price(Decimal("500"), rp)
    assert str(new_price) == "0.00"


def test_api_crud(client, db):
    t = _tenant(db, "rpapi")
    _biz(db, t)
    s = _svc(db, t)
    h = _login(client, t.slug)
    assert client.get("/business/api/rate-plans", headers=h).json()["total"] == 0
    r = client.post("/business/api/rate-plans",
                    json={"service_id": s.id, "name": "BB", "code": "bb",
                          "price_modifier_type": "percent", "price_modifier_value": 15,
                          "meal_plan": "breakfast"},
                    headers=h)
    assert r.status_code == 200
    pid = r.json()["id"]
    r = client.patch(f"/business/api/rate-plans/{pid}",
                     json={"price_modifier_value": 20}, headers=h)
    assert r.status_code == 200
    r = client.delete(f"/business/api/rate-plans/{pid}", headers=h)
    assert r.status_code == 200
    assert r.json()["active"] is False


def test_api_staff_forbidden(client, db):
    t = _tenant(db, "rpapi-staff")
    _biz(db, t, email="staff@biz.test", role="staff")
    s = _svc(db, t)
    h = _login(client, t.slug, "staff@biz.test")
    r = client.post("/business/api/rate-plans",
                    json={"service_id": s.id, "name": "X", "code": "x"}, headers=h)
    assert r.status_code == 403


def test_api_requires_auth(client, db):
    t = _tenant(db, "rpapi-noauth")
    r = client.get("/business/api/rate-plans", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401
