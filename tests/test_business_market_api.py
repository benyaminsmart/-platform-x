"""Tests for Business Market Insights API (Phase 27, Step 3)."""

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


def _tenant(db: Session, slug: str, *, cfg: dict | None = None) -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config=cfg or {"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _biz_user(db: Session, tenant: Tenant, *, email: str = "owner@biz.test") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("OwnerPass123"),
        first_name="O", last_name="X",
        business_role="owner", status="active",
        referral_code=email[:10].upper(),
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db: Session, tenant: Tenant, *, price: float = 500) -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name="R",
        price=Decimal(str(price)), currency="AED", capacity=2,
        attributes={}, image_urls=[], status="active", display_order=0,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


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


# ---------- Auth ----------


@pytest.mark.parametrize("path", [
    "/business/api/market/summary",
    "/business/api/market/position",
    "/business/api/market/region?region=UAE",
    "/business/api/market/insights",
    "/business/api/market/insights/ai",
])
def test_endpoints_require_auth(client: TestClient, sample_tenant: Tenant, path: str) -> None:
    r = client.get(path, headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 401


# ---------- Summary ----------


def test_market_summary_empty_cohort(client: TestClient, db: Session) -> None:
    t = _tenant(db, "self", cfg={"type": "hotel"})
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/market/summary", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["category"] == "hotels"
    assert body["cohort_size"] == 0
    assert body["note"]


def test_market_summary_with_peers(client: TestClient, db: Session) -> None:
    t = _tenant(db, "self", cfg={"type": "hotel"})
    _biz_user(db, t)
    for i, pr in enumerate([300, 600, 900], start=1):
        p = _tenant(db, f"p{i}", cfg={"type": "hotel"})
        _svc(db, p, price=pr)

    tok = _login(client, t.slug)
    r = client.get("/business/api/market/summary", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["cohort_size"] == 3
    assert body["metrics"]["avg_price"]["median"] == 600.0


# ---------- Position ----------


def test_market_position(client: TestClient, db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel", "rating": 4.9})
    _biz_user(db, t_self)
    _svc(db, t_self, price=900)
    for i, (price, rating) in enumerate([(300, 3.5), (400, 4.0), (500, 4.2)], start=1):
        p = _tenant(db, f"p{i}", cfg={"type": "hotel", "rating": rating})
        _svc(db, p, price=price)

    tok = _login(client, t_self.slug)
    r = client.get("/business/api/market/position", headers=_h(tok, t_self.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["cohort_size"] == 3
    assert body["positions"]["avg_price"]["percentile"] == 100.0
    assert body["positions"]["rating"]["percentile"] == 100.0


# ---------- Region ----------


def test_market_region(client: TestClient, db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel", "location": "Downtown, Dubai, UAE"})
    _biz_user(db, t_self)
    _tenant(db, "p1", cfg={"type": "hotel", "location": "Marina, Dubai, UAE"})
    _tenant(db, "p2", cfg={"type": "restaurant", "location": "JBR, Dubai, UAE"})

    tok = _login(client, t_self.slug)
    r = client.get("/business/api/market/region?region=UAE", headers=_h(tok, t_self.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["cohort_size"] == 2
    assert body["categories"]["hotels"] == 1
    assert body["categories"]["restaurants"] == 1


def test_market_region_requires_query(client: TestClient, db: Session) -> None:
    t = _tenant(db, "self", cfg={"type": "hotel"})
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/market/region", headers=_h(tok, t.slug))
    assert r.status_code == 422


# ---------- Insights (deterministic combined) ----------


def test_market_insights_combined(client: TestClient, db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel", "location": "Downtown, Dubai, UAE", "rating": 4.8})
    _biz_user(db, t_self)
    _svc(db, t_self, price=900)
    for i, (price, rating) in enumerate([(300, 3.5), (400, 4.0), (500, 4.2)], start=1):
        p = _tenant(db, f"p{i}", cfg={"type": "hotel", "rating": rating})
        _svc(db, p, price=price)

    tok = _login(client, t_self.slug)
    r = client.get("/business/api/market/insights", headers=_h(tok, t_self.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "fallback"
    assert body["metrics"]["tenant_category"] == "hotels"
    assert len(body["strengths"]) >= 1
    assert body["summary"]
    assert body["advice"]


# ---------- Insights AI ----------


def test_market_insights_ai(client: TestClient, db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _fake(message, *, history=None, provider_name=None):
        return {
            "content": '{"summary": "AI summary text.", "advice": "AI advice text."}',
            "provider": "stub", "model": "x", "tokens_used": 0,
        }
    monkeypatch.setattr(ai_service, "chat", _fake)

    t = _tenant(db, "self-ai", cfg={"type": "hotel", "location": "Dubai, UAE"})
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/market/insights/ai?language=en", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["summary"] == "AI summary text."
    assert body["advice"] == "AI advice text."
    assert body["provider"] == "ai"


def test_market_insights_ai_invalid_language(client: TestClient, db: Session) -> None:
    t = _tenant(db, "self-lang", cfg={"type": "hotel"})
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/market/insights/ai?language=xx", headers=_h(tok, t.slug))
    assert r.status_code == 422


# ---------- Cross-tenant privacy ----------


def test_cross_tenant_no_identity_leak(client: TestClient, db: Session) -> None:
    a = _tenant(db, "self-a", cfg={"type": "hotel"})
    b = _tenant(db, "peer-b-secret-slug", cfg={"type": "hotel", "rating": 4.9})
    _biz_user(db, a)
    _svc(db, b, price=800)

    tok = _login(client, a.slug)
    r = client.get("/business/api/market/summary", headers=_h(tok, a.slug))
    assert r.status_code == 200
    # The peer's slug or id must NOT appear in the response
    text = r.text
    assert "peer-b-secret-slug" not in text
    assert b.id not in text
