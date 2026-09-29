"""Tests for the Leaderboard API (Phase 29, Step 4)."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import leaderboard as lb_service
from app.services import scoring_engine


# ---------- Helpers ----------


def _tenant(db: Session, slug: str, cfg: dict) -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config=cfg)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _biz_user(db: Session, tenant: Tenant, *, email: str = "owner@biz.test") -> User:
    u = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password("OwnerPass123"),
        first_name="Owner",
        last_name="One",
        business_role="owner",
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


# ---------- Public leaderboard ----------


def test_public_leaderboard_empty(client: TestClient) -> None:
    r = client.get("/leaderboard")
    assert r.status_code == 200
    assert r.json() == []


def test_public_leaderboard_returns_scores(client: TestClient, db: Session) -> None:
    _tenant(db, "hotel-a", {"type": "hotel", "rating": 4.8, "reviews_count": 300})
    _tenant(db, "hotel-b", {"type": "hotel", "rating": 4.0, "reviews_count": 100})
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    r = client.get("/leaderboard")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert rows[0]["rank_overall"] == 1
    assert rows[0]["overall_score"] >= rows[1]["overall_score"]
    # reward on rank 1
    assert rows[0]["rewards"]["badge"] == "gold"
    assert rows[1]["rewards"]["badge"] == "silver"


def test_public_leaderboard_filter_by_category(client: TestClient, db: Session) -> None:
    _tenant(db, "h1", {"type": "hotel", "rating": 5.0, "reviews_count": 300})
    _tenant(db, "r1", {"type": "restaurant", "rating": 4.5, "reviews_count": 300})
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    r = client.get("/leaderboard?category=hotels")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["category"] == "hotels"
    assert rows[0]["rank"] == 1  # rank in category


def test_public_leaderboard_invalid_category(client: TestClient) -> None:
    r = client.get("/leaderboard?category=bogus")
    assert r.status_code == 400


def test_public_leaderboard_limit(client: TestClient, db: Session) -> None:
    for i in range(5):
        _tenant(db, f"t-{i}", {"type": "hotel", "rating": 4.0 + i * 0.1, "reviews_count": 100})
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    r = client.get("/leaderboard?limit=2")
    assert len(r.json()) == 2


# ---------- Categories endpoint ----------


def test_categories_endpoint(client: TestClient, db: Session) -> None:
    _tenant(db, "h1", {"type": "hotel", "rating": 5.0, "reviews_count": 300})
    _tenant(db, "h2", {"type": "hotel", "rating": 3.0, "reviews_count": 100})
    _tenant(db, "r1", {"type": "restaurant", "rating": 4.5, "reviews_count": 300})
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    r = client.get("/leaderboard/categories")
    assert r.status_code == 200
    cats = {c["category"]: c for c in r.json()}
    assert cats["hotels"]["tenants"] == 2
    assert cats["hotels"]["top_slug"] == "h1"
    assert cats["restaurants"]["tenants"] == 1
    assert cats["travel"]["tenants"] == 0


# ---------- Business score endpoint ----------


def test_business_score_requires_auth(client: TestClient, sample_tenant: Tenant) -> None:
    r = client.get("/business/api/score", headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 401


def test_business_score_404_when_not_computed(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    tok = _login(client, sample_tenant.slug)
    r = client.get(
        "/business/api/score",
        headers={"Authorization": f"Bearer {tok}", "X-Tenant-Slug": sample_tenant.slug},
    )
    assert r.status_code == 404


def test_business_score_returns_own_score(client: TestClient, db: Session) -> None:
    t = _tenant(db, "my-biz", {"type": "hotel", "rating": 4.5, "reviews_count": 200})
    _biz_user(db, t)
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    tok = _login(client, t.slug)
    r = client.get(
        "/business/api/score",
        headers={"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_id"] == t.id
    assert body["category"] == "hotels"
    assert 0.0 <= body["overall_score"] <= 100.0
    assert "criteria_breakdown" in body
    # Only 1 tenant in leaderboard -> rank 1 -> gold
    assert body["rank_overall"] == 1
    assert body["rewards"]["badge"] == "gold"


def test_business_score_cross_tenant_isolation(client: TestClient, db: Session) -> None:
    a = _tenant(db, "biz-a", {"type": "hotel", "rating": 5.0, "reviews_count": 500})
    b = _tenant(db, "biz-b", {"type": "hotel", "rating": 3.0, "reviews_count": 100})
    _biz_user(db, a, email="owner@a.test")
    _biz_user(db, b, email="owner@b.test")
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    tok_a = _login(client, a.slug, "owner@a.test")
    r = client.get(
        "/business/api/score",
        headers={"Authorization": f"Bearer {tok_a}", "X-Tenant-Slug": a.slug},
    )
    assert r.status_code == 200
    assert r.json()["tenant_id"] == a.id
    # A should be rank 1, B rank 2
    assert r.json()["rank_overall"] == 1


# ---------- Platform recompute ----------


def test_platform_recompute_requires_admin(client: TestClient) -> None:
    r = client.post("/platform/api/leaderboard/recompute")
    assert r.status_code == 401


def test_platform_recompute_current(client: TestClient, admin_client, db: Session) -> None:
    _tenant(db, "h1", {"type": "hotel", "rating": 5.0, "reviews_count": 500})
    _tenant(db, "h2", {"type": "hotel", "rating": 3.0, "reviews_count": 200})

    client, h = admin_client
    r = client.post("/platform/api/leaderboard/recompute", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenants_total"] == 2
    assert body["created"] == 2
    assert body["ranks_assigned"] == 2


def test_platform_recompute_previous(client: TestClient, admin_client, db: Session) -> None:
    _tenant(db, "h1", {"type": "hotel", "rating": 5.0, "reviews_count": 500})
    client, h = admin_client
    r = client.post("/platform/api/leaderboard/recompute?period=previous", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["tenants_total"] == 1
    # Period must be last month
    ps_prev, _ = scoring_engine.previous_period()
    assert body["period_start"] == ps_prev.isoformat()


def test_platform_recompute_invalid_period(client: TestClient, admin_client) -> None:
    client, h = admin_client
    r = client.post("/platform/api/leaderboard/recompute?period=next", headers=h)
    assert r.status_code == 422  # pydantic pattern validation


# ---------- Tips endpoint ----------


def test_business_tips_requires_auth(client: TestClient, sample_tenant: Tenant) -> None:
    r = client.get("/business/api/score/tips", headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 401


def test_business_tips_404_when_not_computed(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _biz_user(db, sample_tenant)
    tok = _login(client, sample_tenant.slug)
    r = client.get(
        "/business/api/score/tips",
        headers={"Authorization": f"Bearer {tok}", "X-Tenant-Slug": sample_tenant.slug},
    )
    assert r.status_code == 404


def test_business_tips_returns_tips(client: TestClient, db: Session) -> None:
    t = _tenant(db, "tips-biz", {"type": "hotel", "rating": 4.0, "reviews_count": 100})
    _biz_user(db, t)
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    tok = _login(client, t.slug)
    r = client.get(
        "/business/api/score/tips",
        headers={"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "weakest" in body
    assert len(body["weakest"]) == 3
    assert "advice" in body
    assert body["advice"]
    # Rank 1 -> no next rank gap
    assert body["next_rank_gap"] is None


def test_business_tips_next_rank_gap_present(client: TestClient, db: Session) -> None:
    a = _tenant(db, "top-a", {"type": "hotel", "rating": 5.0, "reviews_count": 1000})
    b = _tenant(db, "second-b", {"type": "hotel", "rating": 3.0, "reviews_count": 100})
    _biz_user(db, b, email="owner@b.test")
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    tok_b = _login(client, b.slug, "owner@b.test")
    r = client.get(
        "/business/api/score/tips",
        headers={"Authorization": f"Bearer {tok_b}", "X-Tenant-Slug": b.slug},
    )
    assert r.status_code == 200
    gap = r.json()["next_rank_gap"]
    assert gap is not None
    assert gap["target_rank"] == 1
