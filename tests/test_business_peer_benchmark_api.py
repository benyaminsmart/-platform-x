"""Tests for Business Peer Benchmark API (Phase 52, Step 2)."""
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant_with_owner(db, slug, typ="hotel", rating=4.5):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": rating, "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    u = User(tenant_id=t.id, email=f"owner@{slug}.com",
             password_hash=hash_password("OwnerPass123"),
             first_name="O", last_name="X", business_role="owner",
             referral_code=f"OWN{slug[:6].upper()}", status="active")
    db.add(u); db.commit(); db.refresh(u)
    return t, u


def _svc(db, t, price=500):
    s = Service(tenant_id=t.id, type="room", name=f"R-{t.slug}",
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _biz_login(client, slug, email):
    r = client.post("/business/api/login",
                    json={"email": email, "password": "OwnerPass123"},
                    headers={"X-Tenant-Slug": slug})
    if r.status_code != 200:
        # Fallback: some panels accept /auth/login with business_role check
        r = client.post("/auth/login",
                        json={"email": email, "password": "OwnerPass123"},
                        headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_requires_auth(client: TestClient) -> None:
    r = client.get("/business/api/peer-benchmark")
    assert r.status_code == 401


def test_benchmark_with_peers(client: TestClient, db: Session) -> None:
    me, owner = _tenant_with_owner(db, "pb-api-me")
    p1, _ = _tenant_with_owner(db, "pb-api-p1")
    _svc(db, me, price=600)
    _svc(db, p1, price=400)

    token = _biz_login(client, "pb-api-me", owner.email)
    r = client.get("/business/api/peer-benchmark",
                   headers={"Authorization": f"Bearer {token}",
                            "X-Tenant-Slug": "pb-api-me"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["category"] == "hotel"
    metrics = {m["metric"]: m for m in body["metrics"]}
    assert metrics["avg_price"]["self"] == 600.0
    assert metrics["avg_price"]["peer_median"] == 400.0
    assert body["summary"]


def test_benchmark_invalid_language(client: TestClient, db: Session) -> None:
    me, owner = _tenant_with_owner(db, "pb-api-lang")
    token = _biz_login(client, "pb-api-lang", owner.email)
    r = client.get("/business/api/peer-benchmark?language=xx",
                   headers={"Authorization": f"Bearer {token}",
                            "X-Tenant-Slug": "pb-api-lang"})
    assert r.status_code == 422


def test_benchmark_never_exposes_peer_slug(client: TestClient, db: Session) -> None:
    me, owner = _tenant_with_owner(db, "pb-api-self")
    p1, _ = _tenant_with_owner(db, "pb-api-secret-peer")
    _svc(db, me, price=500)
    _svc(db, p1, price=400)

    token = _biz_login(client, "pb-api-self", owner.email)
    r = client.get("/business/api/peer-benchmark",
                   headers={"Authorization": f"Bearer {token}",
                            "X-Tenant-Slug": "pb-api-self"})
    assert r.status_code == 200
    assert "pb-api-secret-peer" not in r.text
