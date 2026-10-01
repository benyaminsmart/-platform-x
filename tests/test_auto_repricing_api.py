"""Tests for Business Auto-Repricing API (Phase 60, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant_with_owner(db, slug, enabled=False):
    cfg = {"type": "hotel", "rating": 4.5, "location": "Dubai"}
    if enabled:
        cfg["auto_repricing_enabled"] = True
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config=cfg)
    db.add(t); db.commit(); db.refresh(t)
    rc = ("OWN" + slug.upper().replace("-", ""))[:30]
    u = User(tenant_id=t.id, email=f"owner@{slug}.com",
             password_hash=hash_password("OwnerPass123"),
             first_name="O", last_name="X", business_role="owner",
             referral_code=rc, status="active")
    db.add(u); db.commit(); db.refresh(u)
    return t, u


def _svc(db, t, price=1000, capacity=2):
    s = Service(tenant_id=t.id, type="room", name="Room",
                price=Decimal(str(price)), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _login(client, slug, email):
    r = client.post("/auth/login",
                    json={"email": email, "password": "OwnerPass123"},
                    headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_status_requires_auth(client: TestClient) -> None:
    r = client.get("/business/api/auto-repricing/status")
    assert r.status_code == 401


def test_status_and_toggle(client: TestClient, db: Session) -> None:
    t, owner = _tenant_with_owner(db, "ar-api-1", enabled=False)
    token = _login(client, t.slug, owner.email)
    h = {"Authorization": f"Bearer {token}"}

    r = client.get("/business/api/auto-repricing/status", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["enabled"] is False

    r = client.post("/business/api/auto-repricing/toggle",
                    json={"enabled": True}, headers=h)
    assert r.status_code == 200
    assert r.json()["enabled"] is True

    r = client.get("/business/api/auto-repricing/status", headers=h)
    assert r.json()["enabled"] is True


def test_preview(client: TestClient, db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t, owner = _tenant_with_owner(db, "ar-api-prev", enabled=True)
    s = _svc(db, t)
    token = _login(client, t.slug, owner.email)
    h = {"Authorization": f"Bearer {token}"}

    r = client.post("/business/api/auto-repricing/preview",
                    json={"service_id": s.id}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["suggested_price"] is not None


def test_preview_service_not_found(client: TestClient, db: Session) -> None:
    t, owner = _tenant_with_owner(db, "ar-api-nf", enabled=True)
    token = _login(client, t.slug, owner.email)
    r = client.post("/business/api/auto-repricing/preview",
                    json={"service_id": "missing"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_apply_changes_price(client: TestClient, db: Session) -> None:
    t, owner = _tenant_with_owner(db, "ar-api-apply", enabled=True)
    s = _svc(db, t, price=1000)
    token = _login(client, t.slug, owner.email)
    h = {"Authorization": f"Bearer {token}"}

    r = client.post("/business/api/auto-repricing/apply",
                    json={"service_id": s.id, "new_price": 1200.0}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["new_price"] == 1200.0

    db.refresh(s)
    assert float(s.price) == 1200.0


def test_apply_cross_tenant_isolation(client: TestClient, db: Session) -> None:
    t1, owner1 = _tenant_with_owner(db, "ar-api-iso-1", enabled=True)
    t2, owner2 = _tenant_with_owner(db, "ar-api-iso-2", enabled=True)
    s2 = _svc(db, t2, price=500)
    token1 = _login(client, t1.slug, owner1.email)
    r = client.post("/business/api/auto-repricing/apply",
                    json={"service_id": s2.id, "new_price": 999.0},
                    headers={"Authorization": f"Bearer {token1}"})
    assert r.status_code == 404
