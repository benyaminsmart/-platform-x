"""Tests for Business Pricing Rules API (Phase 22, Step 3)."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


# ---------- Helpers ----------


def _biz_user(db: Session, tenant: Tenant, *, email: str = "owner@biz.test", role: str = "owner") -> User:
    u = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password("OwnerPass123"),
        first_name="Owner",
        last_name="One",
        business_role=role,
        status="active",
        referral_code=email[:10].upper(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client: TestClient, slug: str, email: str = "owner@biz.test") -> str:
    r = client.post(
        "/business/api/auth/login",
        json={"email": email, "password": "OwnerPass123"},
        headers={"X-Tenant-Slug": slug},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(tok: str, slug: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": slug}


def _svc(db: Session, tenant: Tenant, *, name: str = "R", price: float = 500) -> Service:
    s = Service(
        tenant_id=tenant.id,
        type="room",
        name=name,
        price=Decimal(str(price)),
        currency="AED",
        capacity=2,
        attributes={},
        image_urls=[],
        status="active",
        display_order=0,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ---------- Auth guards ----------


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/business/api/pricing/rules"),
        ("POST", "/business/api/pricing/rules"),
        ("POST", "/business/api/pricing/preview"),
    ],
)
def test_endpoints_require_auth(client: TestClient, sample_tenant: Tenant, method: str, path: str) -> None:
    headers = {"X-Tenant-Slug": sample_tenant.slug}
    if method == "GET":
        r = client.get(path, headers=headers)
    else:
        r = client.post(path, json={}, headers=headers)
    assert r.status_code == 401


# ---------- CRUD ----------


def test_create_and_list_rule(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    tok = _login(client, sample_tenant.slug)
    h = _h(tok, sample_tenant.slug)

    # empty
    r = client.get("/business/api/pricing/rules", headers=h)
    assert r.status_code == 200
    assert r.json() == []

    # create
    r = client.post(
        "/business/api/pricing/rules",
        json={
            "name": "Weekend boost",
            "rule_type": "weekend",
            "conditions": {"days_of_week": [5, 6]},
            "action": {"type": "percent", "value": 20},
            "priority": 100,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Weekend boost"
    assert body["rule_type"] == "weekend"
    assert body["action"]["value"] == 20
    rid = body["id"]

    # list has one
    r = client.get("/business/api/pricing/rules", headers=h)
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == rid

    # get by id
    r = client.get(f"/business/api/pricing/rules/{rid}", headers=h)
    assert r.status_code == 200
    assert r.json()["id"] == rid


def test_create_rule_invalid_type(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    tok = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/pricing/rules",
        json={"name": "x", "rule_type": "bogus", "action": {"type": "percent", "value": 10}},
        headers=_h(tok, sample_tenant.slug),
    )
    assert r.status_code == 400
    assert "rule_type" in r.json()["detail"]


def test_create_rule_invalid_action(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    tok = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/pricing/rules",
        json={"name": "x", "rule_type": "weekend", "action": {"type": "bogus", "value": 10}},
        headers=_h(tok, sample_tenant.slug),
    )
    assert r.status_code == 400
    assert "action.type" in r.json()["detail"]


def test_create_rule_missing_action_value(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    tok = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/pricing/rules",
        json={"name": "x", "rule_type": "weekend", "action": {"type": "percent"}},
        headers=_h(tok, sample_tenant.slug),
    )
    assert r.status_code == 400
    assert "value" in r.json()["detail"]


def test_update_rule(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    tok = _login(client, sample_tenant.slug)
    h = _h(tok, sample_tenant.slug)

    r = client.post(
        "/business/api/pricing/rules",
        json={
            "name": "A", "rule_type": "weekend",
            "conditions": {"days_of_week": [5]},
            "action": {"type": "percent", "value": 10},
        },
        headers=h,
    )
    rid = r.json()["id"]

    r = client.patch(
        f"/business/api/pricing/rules/{rid}",
        json={"name": "A+", "priority": 42, "active": False},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "A+"
    assert r.json()["priority"] == 42
    assert r.json()["active"] is False


def test_update_rule_invalid_action(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    tok = _login(client, sample_tenant.slug)
    h = _h(tok, sample_tenant.slug)
    r = client.post(
        "/business/api/pricing/rules",
        json={"name": "x", "rule_type": "weekend", "action": {"type": "percent", "value": 10}},
        headers=h,
    )
    rid = r.json()["id"]
    r = client.patch(
        f"/business/api/pricing/rules/{rid}",
        json={"action": {"type": "nope", "value": 5}},
        headers=h,
    )
    assert r.status_code == 400


def test_delete_rule_soft(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    tok = _login(client, sample_tenant.slug)
    h = _h(tok, sample_tenant.slug)
    r = client.post(
        "/business/api/pricing/rules",
        json={"name": "x", "rule_type": "weekend", "action": {"type": "percent", "value": 10}},
        headers=h,
    )
    rid = r.json()["id"]
    r = client.delete(f"/business/api/pricing/rules/{rid}", headers=h)
    assert r.status_code == 200
    # still exists, but inactive
    r = client.get(f"/business/api/pricing/rules/{rid}", headers=h)
    assert r.json()["active"] is False


# ---------- Role-based access ----------


def test_staff_cannot_create(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant, email="staff@biz.test", role="staff")
    tok = _login(client, sample_tenant.slug, "staff@biz.test")
    r = client.post(
        "/business/api/pricing/rules",
        json={"name": "x", "rule_type": "weekend", "action": {"type": "percent", "value": 10}},
        headers=_h(tok, sample_tenant.slug),
    )
    assert r.status_code == 403


def test_staff_can_read(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant, email="staff@biz.test", role="staff")
    tok = _login(client, sample_tenant.slug, "staff@biz.test")
    r = client.get("/business/api/pricing/rules", headers=_h(tok, sample_tenant.slug))
    assert r.status_code == 200


# ---------- Cross-tenant isolation ----------


def test_cross_tenant_rule_isolation(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    # Tenant A
    _biz_user(db, sample_tenant, email="owner@a.test")
    tok_a = _login(client, sample_tenant.slug, "owner@a.test")
    ha = _h(tok_a, sample_tenant.slug)
    r = client.post(
        "/business/api/pricing/rules",
        json={"name": "A-rule", "rule_type": "weekend", "action": {"type": "percent", "value": 10}},
        headers=ha,
    )
    rid_a = r.json()["id"]

    # Tenant B
    tb = Tenant(slug="other-b", name="B", tier="starter", status="active", config={})
    db.add(tb)
    db.commit()
    db.refresh(tb)
    _biz_user(db, tb, email="owner@b.test")
    tok_b = _login(client, tb.slug, "owner@b.test")
    hb = _h(tok_b, tb.slug)

    # B sees no rules
    r = client.get("/business/api/pricing/rules", headers=hb)
    assert r.json() == []

    # B cannot get A's rule
    r = client.get(f"/business/api/pricing/rules/{rid_a}", headers=hb)
    assert r.status_code == 404

    # B cannot update A's rule
    r = client.patch(f"/business/api/pricing/rules/{rid_a}", json={"name": "hack"}, headers=hb)
    assert r.status_code == 404

    # B cannot delete A's rule
    r = client.delete(f"/business/api/pricing/rules/{rid_a}", headers=hb)
    assert r.status_code == 404


# ---------- Preview ----------


def test_preview_no_rules(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    s = _svc(db, sample_tenant, price=500)
    tok = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/pricing/preview",
        json={"service_id": s.id, "check_in": "2026-10-03"},
        headers=_h(tok, sample_tenant.slug),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["original_price"] == "500.00"
    assert body["final_price"] == "500.00"
    assert body["applied_rules"] == []


def test_preview_with_weekend_rule(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    s = _svc(db, sample_tenant, price=500)
    tok = _login(client, sample_tenant.slug)
    h = _h(tok, sample_tenant.slug)

    client.post(
        "/business/api/pricing/rules",
        json={
            "name": "Weekend",
            "rule_type": "weekend",
            "conditions": {"days_of_week": [5, 6]},
            "action": {"type": "percent", "value": 20},
        },
        headers=h,
    )
    r = client.post(
        "/business/api/pricing/preview",
        json={"service_id": s.id, "check_in": "2026-10-03"},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["original_price"] == "500.00"
    assert body["final_price"] == "600.00"
    assert len(body["applied_rules"]) == 1


def test_preview_service_not_found(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    tok = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/pricing/preview",
        json={"service_id": "does-not-exist", "check_in": "2026-10-03"},
        headers=_h(tok, sample_tenant.slug),
    )
    assert r.status_code == 404


def test_preview_cross_tenant_service_blocked(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant, email="owner@a.test")
    tok_a = _login(client, sample_tenant.slug, "owner@a.test")

    tb = Tenant(slug="other-b", name="B", tier="starter", status="active", config={})
    db.add(tb)
    db.commit()
    db.refresh(tb)
    s_b = _svc(db, tb, name="B-room", price=900)

    r = client.post(
        "/business/api/pricing/preview",
        json={"service_id": s_b.id, "check_in": "2026-10-03"},
        headers=_h(tok_a, sample_tenant.slug),
    )
    assert r.status_code == 404
