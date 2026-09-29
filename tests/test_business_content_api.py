"""Tests for Business AI Content endpoints (Phase 23, Step 2)."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "content-biz", cfg: dict | None = None) -> Tenant:
    t = Tenant(
        slug=slug, name="Content Hotel", tier="starter", status="active",
        config=cfg or {
            "type": "hotel",
            "location": "Dubai, UAE",
            "rating": 4.7,
            "reviews_count": 300,
        },
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


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


def _svc(db: Session, tenant: Tenant, *, name: str = "Deluxe Room") -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name=name,
        price=Decimal("850"), currency="AED", capacity=2,
        attributes={"view": "sea"}, image_urls=[], status="active", display_order=0,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _h(tok: str, slug: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": slug}


# ---------- Auth guards ----------


@pytest.mark.parametrize(
    "path",
    [
        "/business/api/ai/content/tagline",
    ],
)
def test_content_endpoints_require_auth(client: TestClient, sample_tenant: Tenant, path: str) -> None:
    r = client.post(path, json={"language": "en", "tone": "professional"},
                    headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 401


# ---------- Generate service description ----------


def test_generate_service_description(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    s = _svc(db, t)
    tok = _login(client, t.slug)

    r = client.post(
        f"/business/api/ai/content/service/{s.id}",
        json={"language": "en", "tone": "professional"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["language"] == "en"
    assert body["tone"] == "professional"
    assert body["description"]
    assert body["provider"] in ("ai", "fallback")


def test_generate_service_description_invalid_language(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    s = _svc(db, t)
    tok = _login(client, t.slug)

    # Regex pattern in schema returns 422 on invalid language
    r = client.post(
        f"/business/api/ai/content/service/{s.id}",
        json={"language": "xx", "tone": "professional"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 422


def test_generate_service_description_service_not_found(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.post(
        "/business/api/ai/content/service/does-not-exist",
        json={"language": "en", "tone": "professional"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 404


def test_generate_service_description_cross_tenant_blocked(client: TestClient, db: Session) -> None:
    a = _tenant(db, "biz-a")
    b = _tenant(db, "biz-b")
    _biz_user(db, a, email="owner@a.test")
    s_b = _svc(db, b, name="B-room")
    tok = _login(client, a.slug, "owner@a.test")

    r = client.post(
        f"/business/api/ai/content/service/{s_b.id}",
        json={"language": "en", "tone": "professional"},
        headers=_h(tok, a.slug),
    )
    assert r.status_code == 404


def test_generate_service_description_all_languages(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    s = _svc(db, t)
    tok = _login(client, t.slug)
    for lang in ["en", "ar", "fil", "hi"]:
        r = client.post(
            f"/business/api/ai/content/service/{s.id}",
            json={"language": lang, "tone": "professional"},
            headers=_h(tok, t.slug),
        )
        assert r.status_code == 200
        assert r.json()["language"] == lang


# ---------- Apply (save) ----------


def test_apply_service_description(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t, role="owner")
    s = _svc(db, t)
    tok = _login(client, t.slug)

    r = client.post(
        f"/business/api/ai/content/service/{s.id}/apply",
        json={"language": "en", "tone": "luxury"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # Description saved in DB
    db.refresh(s)
    assert s.description == body["description"]


def test_apply_staff_forbidden(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t, email="staff@biz.test", role="staff")
    s = _svc(db, t)
    tok = _login(client, t.slug, "staff@biz.test")

    r = client.post(
        f"/business/api/ai/content/service/{s.id}/apply",
        json={"language": "en", "tone": "professional"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 403


def test_apply_manager_allowed(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t, email="mgr@biz.test", role="manager")
    s = _svc(db, t)
    tok = _login(client, t.slug, "mgr@biz.test")

    r = client.post(
        f"/business/api/ai/content/service/{s.id}/apply",
        json={"language": "en", "tone": "professional"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 200


# ---------- Tagline ----------


def test_generate_tagline(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.post(
        "/business/api/ai/content/tagline",
        json={"language": "en", "tone": "professional"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tagline"]
    assert body["language"] == "en"


def test_generate_tagline_all_languages(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    for lang in ["en", "ar", "fil", "hi"]:
        r = client.post(
            "/business/api/ai/content/tagline",
            json={"language": lang, "tone": "professional"},
            headers=_h(tok, t.slug),
        )
        assert r.status_code == 200
        assert r.json()["language"] == lang


# ---------- Image keywords ----------


def test_suggest_image_keywords(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    s = _svc(db, t, name="Deluxe Sea View Suite")
    tok = _login(client, t.slug)
    r = client.post(
        f"/business/api/ai/content/image-keywords/{s.id}",
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "keywords" in body
    assert isinstance(body["keywords"], list)
    assert body["query"]
    assert "unsplash" in body["unsplash_search_url"]
    assert "unsplash" in body["unsplash_source_url"]


def test_suggest_image_keywords_cross_tenant(client: TestClient, db: Session) -> None:
    a = _tenant(db, "ai-a")
    b = _tenant(db, "ai-b")
    _biz_user(db, a, email="owner@a.test")
    s_b = _svc(db, b, name="B-only")
    tok = _login(client, a.slug, "owner@a.test")
    r = client.post(
        f"/business/api/ai/content/image-keywords/{s_b.id}",
        headers=_h(tok, a.slug),
    )
    assert r.status_code == 404
