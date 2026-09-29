"""Tests for Business API Keys API + page (Phase 14, Step 5)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db: Session, slug: str = "bkeys") -> Tenant:
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
    r = client.get("/business/api/keys", headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 401


# ---------- List ----------


def test_list_empty(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.get("/business/api/keys", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert "read:services" in body["allowed_scopes"]


# ---------- Create ----------


def test_create_key(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/keys",
        json={"name": "Backend", "scopes": ["read:services", "read:bookings"]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plaintext"].startswith("pk_live_")
    assert body["key"]["name"] == "Backend"
    assert set(body["key"]["scopes"]) == {"read:services", "read:bookings"}


def test_create_staff_forbidden(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant, email="staff@biz.test", role="staff")
    h = _login(client, sample_tenant.slug, "staff@biz.test")
    r = client.post(
        "/business/api/keys",
        json={"name": "x", "scopes": ["read:services"]},
        headers=h,
    )
    assert r.status_code == 403


def test_create_invalid_scope(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/keys",
        json={"name": "x", "scopes": ["bogus:scope"]},
        headers=h,
    )
    assert r.status_code == 400


def test_create_empty_name_validation(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post("/business/api/keys", json={"name": "", "scopes": ["read:services"]}, headers=h)
    assert r.status_code == 422


def test_create_expires_in_days(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/keys",
        json={"name": "temp", "scopes": ["read:services"], "expires_in_days": 30},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["key"]["expires_at"] is not None


# ---------- Revoke ----------


def test_revoke(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    created = client.post(
        "/business/api/keys",
        json={"name": "x", "scopes": ["read:services"]},
        headers=h,
    ).json()
    kid = created["key"]["id"]

    r = client.post(f"/business/api/keys/{kid}/revoke", headers=h)
    assert r.status_code == 200
    assert r.json()["active"] is False

    # Now list shows inactive
    listing = client.get("/business/api/keys", headers=h).json()
    assert listing["items"][0]["active"] is False


def test_revoke_unknown(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    h = _login(client, sample_tenant.slug)
    r = client.post("/business/api/keys/does-not-exist/revoke", headers=h)
    assert r.status_code == 404


# ---------- Page ----------


def test_api_keys_page_renders(client: TestClient) -> None:
    r = client.get("/business/api-keys")
    assert r.status_code == 200
    html = r.text
    assert "API Keys" in html
    assert 'id="ak-list"' in html
    assert 'id="ak-modal"' in html
    assert 'id="ak-new-btn"' in html
    assert 'id="ak-show-modal"' in html


def test_api_keys_page_uses_correct_apis(client: TestClient) -> None:
    r = client.get("/business/api-keys")
    html = r.text
    assert "/business/api/keys" in html
    assert "/revoke" in html
    assert "/business/api/me" in html
