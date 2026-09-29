"""Tests for Business Webhooks API + UI (Phase 14, Step 6)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db: Session, slug: str = "bwh") -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _biz(db: Session, tenant: Tenant, *, email: str = "owner@biz.test", role: str = "owner") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("OwnerPass123"),
        first_name="O", last_name="X",
        business_role=role, status="active",
        referral_code=email[:10].upper(),
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _login(client: TestClient, slug: str, email: str = "owner@biz.test") -> dict:
    r = client.post(
        "/business/api/auth/login",
        json={"email": email, "password": "OwnerPass123"},
        headers={"X-Tenant-Slug": slug},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Tenant-Slug": slug}


# ---------- Auth ----------


def test_list_requires_auth(client: TestClient, sample_tenant: Tenant) -> None:
    r = client.get("/business/api/webhooks", headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 401


# ---------- List ----------


def test_list_empty(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.get("/business/api/webhooks", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert "booking.created" in body["allowed_events"]


# ---------- Create ----------


def test_create_webhook(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/webhooks",
        json={
            "name": "Backend",
            "url": "https://example.com/hooks/px",
            "events": ["booking.created", "payment.paid"],
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plaintext_secret"].startswith("whsec_")
    assert body["webhook"]["name"] == "Backend"
    assert set(body["webhook"]["events"]) == {"booking.created", "payment.paid"}


def test_create_staff_forbidden(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant, email="staff@biz.test", role="staff")
    h = _login(client, sample_tenant.slug, "staff@biz.test")
    r = client.post(
        "/business/api/webhooks",
        json={"name": "x", "url": "https://example.com/h", "events": ["booking.created"]},
        headers=h,
    )
    assert r.status_code == 403


def test_create_invalid_url(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/webhooks",
        json={"name": "x", "url": "ftp://example.com", "events": ["booking.created"]},
        headers=h,
    )
    assert r.status_code == 400


def test_create_invalid_event(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/webhooks",
        json={"name": "x", "url": "https://example.com/h", "events": ["bogus.event"]},
        headers=h,
    )
    assert r.status_code == 400


def test_create_http_public_rejected(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/webhooks",
        json={"name": "x", "url": "http://example.com/h", "events": ["booking.created"]},
        headers=h,
    )
    assert r.status_code == 400


def test_create_localhost_http_allowed(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/webhooks",
        json={"name": "Local", "url": "http://127.0.0.1:9000/hook", "events": ["booking.created"]},
        headers=h,
    )
    assert r.status_code == 200


# ---------- Delete ----------


def test_delete(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    created = client.post(
        "/business/api/webhooks",
        json={"name": "x", "url": "https://example.com/h", "events": ["booking.created"]},
        headers=h,
    ).json()
    wid = created["webhook"]["id"]

    r = client.post(f"/business/api/webhooks/{wid}/delete", headers=h)
    assert r.status_code == 200
    assert r.json()["active"] is False


def test_delete_unknown(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post("/business/api/webhooks/does-not-exist/delete", headers=h)
    assert r.status_code == 404


# ---------- Cross-tenant ----------


def test_cross_tenant_isolated(client: TestClient, db: Session) -> None:
    a = _tenant(db, "bwh-a")
    b = _tenant(db, "bwh-b")
    _biz(db, a, email="owner@a.test")
    _biz(db, b, email="owner@b.test")
    h_a = _login(client, a.slug, "owner@a.test")
    h_b = _login(client, b.slug, "owner@b.test")

    client.post(
        "/business/api/webhooks",
        json={"name": "B", "url": "https://example.com/h", "events": ["booking.created"]},
        headers=h_b,
    )

    a_list = client.get("/business/api/webhooks", headers=h_a).json()
    assert a_list["total"] == 0


# ---------- Page ----------


def test_api_keys_page_has_webhooks_ui(client: TestClient) -> None:
    r = client.get("/business/api-keys")
    assert r.status_code == 200
    html = r.text
    assert 'id="wh-list"' in html
    assert 'id="wh-modal"' in html
    assert 'id="wh-new-btn"' in html
    assert 'id="wh-create-btn"' in html
    assert "/business/api/webhooks" in html
