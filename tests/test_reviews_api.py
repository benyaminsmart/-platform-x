"""Tests for Review API (Phase 28, Step 3)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "rv-api") -> Tenant:
    t = Tenant(slug=slug, name="Review API Biz", tier="starter", status="active", config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db: Session, tenant: Tenant, email: str = "g@x.com") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("GuestPass123"),
        first_name="G", last_name="X",
        referral_code=email[:10].upper(),
        status="active",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _biz(db: Session, tenant: Tenant, email: str = "owner@biz.test", role: str = "owner") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("OwnerPass123"),
        first_name="O", last_name="X",
        business_role=role, status="active",
        referral_code=email[:10].upper(),
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db: Session, tenant: Tenant, user: User) -> Booking:
    ci = date.today() - timedelta(days=5)
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
        guests=1, amount=Decimal("500"), discount=Decimal("0"),
        total_amount=Decimal("500"), currency="AED",
        status="confirmed", payment_status="paid",
    )
    db.add(b); db.commit(); db.refresh(b)
    return b


def _guest_token(client: TestClient, tenant: Tenant, email: str = "g@x.com") -> dict:
    r = client.post(
        "/auth/register",
        json={"email": email, "password": "GuestPass123", "first_name": "G", "last_name": "X"},
        headers={"X-Tenant-Slug": tenant.slug},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Tenant-Slug": tenant.slug}


def _biz_token(client: TestClient, tenant: Tenant, email: str = "owner@biz.test") -> dict:
    r = client.post(
        "/business/api/auth/login",
        json={"email": email, "password": "OwnerPass123"},
        headers={"X-Tenant-Slug": tenant.slug},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Tenant-Slug": tenant.slug}


# ---------- Public ----------


def test_public_tenant_reviews_empty(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    r = client.get(f"/reviews/tenant/{t.slug}")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_public_tenant_not_found(client: TestClient) -> None:
    r = client.get("/reviews/tenant/does-not-exist")
    assert r.status_code == 404


def test_public_shows_published_only(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    # use sample_tenant because slug "demo" exists in tests as the default
    u = _user(db, sample_tenant, "gu1@x.com")
    from app.services import review_service
    r1 = review_service.create_review(db, tenant=sample_tenant, user=u, rating=5, content="Amazing stay, loved it")
    r2 = review_service.create_review(db, tenant=sample_tenant, user=u, rating=3, content="It was okay, nothing special")
    review_service.hide_review(db, sample_tenant, r2.id)

    resp = client.get(f"/reviews/tenant/{sample_tenant.slug}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == r1.id


# ---------- User create ----------


def test_create_review_requires_auth(client: TestClient, sample_tenant: Tenant) -> None:
    r = client.post(
        "/reviews",
        json={"rating": 5, "content": "Amazing stay, loved it"},
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert r.status_code == 401


def test_create_review_ok(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    # register a guest in sample_tenant
    reg = client.post(
        "/auth/register",
        json={"email": "newguest@x.com", "password": "GuestPass123", "first_name": "G", "last_name": "X"},
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    h = {"Authorization": f"Bearer {reg.json()['access_token']}", "X-Tenant-Slug": sample_tenant.slug}

    r = client.post(
        "/reviews",
        json={"rating": 5, "content": "Amazing stay, loved every minute of it", "title": "Perfect"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["rating"] == 5
    assert body["sentiment"] == "positive"
    assert body["verified"] is False


def test_create_review_invalid_rating(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    reg = client.post(
        "/auth/register",
        json={"email": "g2@x.com", "password": "GuestPass123", "first_name": "G", "last_name": "X"},
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    h = {"Authorization": f"Bearer {reg.json()['access_token']}", "X-Tenant-Slug": sample_tenant.slug}
    r = client.post("/reviews", json={"rating": 10, "content": "Nice place ok ok"}, headers=h)
    assert r.status_code == 422


def test_create_review_verified_with_booking(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    # create user first
    reg = client.post(
        "/auth/register",
        json={"email": "verified@x.com", "password": "GuestPass123", "first_name": "V", "last_name": "X"},
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    tok = reg.json()["access_token"]
    h = {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": sample_tenant.slug}

    # get user id from /auth/me
    me = client.get("/auth/me", headers=h).json()
    u = db.query(User).filter(User.id == me["id"]).one()
    b = _booking(db, sample_tenant, u)

    r = client.post(
        "/reviews",
        json={"rating": 5, "content": "Verified stay, loved it", "booking_id": b.id},
        headers=h,
    )
    assert r.status_code == 201
    assert r.json()["verified"] is True


# ---------- My reviews ----------


def test_my_reviews(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    reg = client.post(
        "/auth/register",
        json={"email": "mine@x.com", "password": "GuestPass123", "first_name": "M", "last_name": "X"},
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    h = {"Authorization": f"Bearer {reg.json()['access_token']}", "X-Tenant-Slug": sample_tenant.slug}
    client.post("/reviews", json={"rating": 5, "content": "Loved the stay here"}, headers=h)
    client.post("/reviews", json={"rating": 4, "content": "Good overall experience"}, headers=h)

    r = client.get("/reviews/mine", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 2


# ---------- Business: list, summary, respond ----------


def test_business_list_requires_auth(client: TestClient, sample_tenant: Tenant) -> None:
    r = client.get("/business/api/reviews", headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 401


def test_business_list_and_summary(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    g = _user(db, sample_tenant, "gg@x.com")
    from app.services import review_service
    review_service.create_review(db, tenant=sample_tenant, user=g, rating=5, content="Amazing stay, loved it")
    review_service.create_review(db, tenant=sample_tenant, user=g, rating=4, content="Good overall experience")

    h = _biz_token(client, sample_tenant)
    r = client.get("/business/api/reviews", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 2

    s = client.get("/business/api/reviews/summary", headers=h)
    assert s.status_code == 200
    assert s.json()["total"] == 2


def test_business_hide_requires_role(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant, email="staff@biz.test", role="staff")
    g = _user(db, sample_tenant, "gs@x.com")
    from app.services import review_service
    r = review_service.create_review(db, tenant=sample_tenant, user=g, rating=5, content="Amazing stay, loved it")

    h = _biz_token(client, sample_tenant, "staff@biz.test")
    resp = client.post(f"/business/api/reviews/{r.id}/hide", headers=h)
    assert resp.status_code == 403


def test_business_hide_owner_ok(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    g = _user(db, sample_tenant, "go@x.com")
    from app.services import review_service
    r = review_service.create_review(db, tenant=sample_tenant, user=g, rating=5, content="Amazing stay, loved it")

    h = _biz_token(client, sample_tenant)
    resp = client.post(f"/business/api/reviews/{r.id}/hide", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "hidden"


def test_business_respond_manual(client: TestClient, db: Session, sample_tenant: Tenant) -> None:
    _biz(db, sample_tenant)
    g = _user(db, sample_tenant, "gm@x.com")
    from app.services import review_service
    r = review_service.create_review(db, tenant=sample_tenant, user=g, rating=5, content="Amazing stay, loved it")

    h = _biz_token(client, sample_tenant)
    resp = client.post(
        f"/business/api/reviews/{r.id}/respond",
        json={"response_text": "Thank you so much!", "language": "en", "tone": "friendly", "use_ai": False},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["response_text"] == "Thank you so much!"
    assert resp.json()["response_provider"] == "manual"


def test_business_respond_ai(client: TestClient, db: Session, sample_tenant: Tenant, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _fake(message, *, history=None, provider_name=None):
        return {"content": "Thank you for your kind words!", "provider": "stub", "model": "x", "tokens_used": 0}
    monkeypatch.setattr(ai_service, "chat", _fake)

    _biz(db, sample_tenant)
    g = _user(db, sample_tenant, "gai@x.com")
    from app.services import review_service
    r = review_service.create_review(db, tenant=sample_tenant, user=g, rating=5, content="Amazing stay, loved it")

    h = _biz_token(client, sample_tenant)
    resp = client.post(
        f"/business/api/reviews/{r.id}/respond",
        json={"response_text": None, "language": "en", "tone": "professional", "use_ai": True},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["response_provider"] == "ai"


def test_business_respond_preview(client: TestClient, db: Session, sample_tenant: Tenant, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _fake(message, *, history=None, provider_name=None):
        return {"content": "Preview reply text.", "provider": "stub", "model": "x", "tokens_used": 0}
    monkeypatch.setattr(ai_service, "chat", _fake)

    _biz(db, sample_tenant)
    g = _user(db, sample_tenant, "gp@x.com")
    from app.services import review_service
    r = review_service.create_review(db, tenant=sample_tenant, user=g, rating=4, content="Good experience overall")

    h = _biz_token(client, sample_tenant)
    resp = client.post(
        f"/business/api/reviews/{r.id}/respond/preview",
        json={"language": "en", "tone": "warm"},
        headers=h,
    )
    assert resp.status_code == 200
    assert "Preview" in resp.json()["content"]


def test_business_polish_preview(client: TestClient, db: Session, sample_tenant: Tenant, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _fake(message, *, history=None, provider_name=None):
        return {"content": "Polished version here.", "provider": "stub", "model": "x", "tokens_used": 0}
    monkeypatch.setattr(ai_service, "chat", _fake)

    _biz(db, sample_tenant)
    h = _biz_token(client, sample_tenant)
    resp = client.post(
        "/business/api/reviews/polish",
        json={"raw_text": "room clean and staff nice", "rating": 5, "language": "en"},
        headers=h,
    )
    assert resp.status_code == 200
    assert "Polished" in resp.json()["content"]


# ---------- Cross-tenant ----------


def test_cross_tenant_isolation(client: TestClient, db: Session) -> None:
    a = _tenant(db, "rv-a")
    b = _tenant(db, "rv-b")
    _biz(db, a, email="owner@a.test")
    gb = _user(db, b, "gb@x.com")
    from app.services import review_service
    rb = review_service.create_review(db, tenant=b, user=gb, rating=5, content="Amazing stay at B")

    h_a = _biz_token(client, a, "owner@a.test")
    # A should not see B's reviews
    resp = client.get("/business/api/reviews", headers=h_a)
    assert resp.json()["total"] == 0
    # A cannot hide B's review
    resp = client.post(f"/business/api/reviews/{rb.id}/hide", headers=h_a)
    assert resp.status_code == 404
