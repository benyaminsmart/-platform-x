"""Tests for Business Settings API + UI (Phase 66, Step 1)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User


def _tenant_with_owner(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "rating": 4.5, "location": "Dubai",
                       "currency": "AED", "contact": {"phone": "+971-4-000-0000",
                       "email": f"info@{slug}.com"},
                       "amenities": ["Pool", "WiFi"]})
    db.add(t); db.commit(); db.refresh(t)
    rc = ("OWN" + slug.upper().replace("-", ""))[:30]
    u = User(tenant_id=t.id, email=f"owner@{slug}.com",
             password_hash=hash_password("OwnerPass123"),
             first_name="O", last_name="X", business_role="owner",
             referral_code=rc, status="active")
    db.add(u); db.commit(); db.refresh(u)
    return t, u


def _login(client, slug, email):
    r = client.post("/auth/login",
                    json={"email": email, "password": "OwnerPass123"},
                    headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_settings_requires_auth(client: TestClient) -> None:
    r = client.get("/business/api/settings")
    assert r.status_code == 401


def test_get_settings(client: TestClient, db: Session) -> None:
    t, owner = _tenant_with_owner(db, "bs-api-1")
    token = _login(client, t.slug, owner.email)
    r = client.get("/business/api/settings",
                   headers={"Authorization": f"Bearer {token}",
                            "X-Tenant-Slug": t.slug})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == t.slug
    assert body["currency"] == "AED"
    assert "+971-4-000-0000" in body["phone"]
    assert "Pool" in body["amenities"]


def test_update_settings(client: TestClient, db: Session) -> None:
    t, owner = _tenant_with_owner(db, "bs-api-2")
    token = _login(client, t.slug, owner.email)
    h = {"Authorization": f"Bearer {token}", "X-Tenant-Slug": t.slug,
         "Content-Type": "application/json"}
    r = client.patch("/business/api/settings",
                     json={"tagline": "New tagline", "currency": "USD",
                           "amenities": ["Gym", "Restaurant"]},
                     headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tagline"] == "New tagline"
    assert body["currency"] == "USD"
    assert body["amenities"] == ["Gym", "Restaurant"]


def test_update_settings_staff_forbidden(client: TestClient, db: Session) -> None:
    t, _ = _tenant_with_owner(db, "bs-api-staff")
    # create a staff user
    rc = "STAFF" + t.slug.upper()[:6]
    staff = User(tenant_id=t.id, email=f"staff@{t.slug}.com",
                 password_hash=hash_password("OwnerPass123"),
                 first_name="S", last_name="X", business_role="staff",
                 referral_code=rc, status="active")
    db.add(staff); db.commit(); db.refresh(staff)
    token = _login(client, t.slug, staff.email)
    r = client.patch("/business/api/settings",
                     json={"tagline": "X"},
                     headers={"Authorization": f"Bearer {token}",
                              "X-Tenant-Slug": t.slug})
    assert r.status_code == 403


def test_settings_page_renders(client: TestClient) -> None:
    r = client.get("/business/settings")
    assert r.status_code == 200
    body = r.text
    assert "Business Settings" in body
    assert "st-tagline" in body


def test_settings_page_calls_api(client: TestClient) -> None:
    r = client.get("/business/settings")
    body = r.text
    assert "/business/api/settings" in body
    assert "st-save" in body
