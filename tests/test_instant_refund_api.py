"""Tests for Instant Refund AI API (Phase 54, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com", tier="welcome"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper() + tier[:2].upper(),
             status="active", tier=tier)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, days=10, amount=1000):
    ci = date.today() + timedelta(days=days)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci,
                check_out=ci + timedelta(days=1), guests=1,
                amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def _login(client, slug, email):
    r = client.post("/auth/login", json={"email": email, "password": "Pass1234"},
                    headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_ai_refund_requires_auth(client: TestClient) -> None:
    r = client.get("/bookings/x/ai-refund")
    assert r.status_code == 401


def test_ai_refund_ok(client: TestClient, db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_RATIONALE", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ir-api-1")
    u = _user(db, t, "u@x.com", tier="gold")
    b = _booking(db, t, u, days=10, amount=1000)
    token = _login(client, t.slug, u.email)
    r = client.get(f"/bookings/{b.id}/ai-refund",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["booking_id"] == b.id
    assert body["base_pct"] == 100
    assert body["suggested_pct"] >= 100 or body["suggested_pct"] == 100
    assert body["rationale"] == "AI_RATIONALE"
    assert body["provider"] == "ai"


def test_ai_refund_invalid_language(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ir-api-lang")
    u = _user(db, t, "lang@x.com")
    b = _booking(db, t, u)
    token = _login(client, t.slug, u.email)
    r = client.get(f"/bookings/{b.id}/ai-refund?language=xx",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_ai_refund_cross_user_isolation(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ir-api-iso")
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    b = _booking(db, t, u1)
    tok2 = _login(client, t.slug, u2.email)
    r = client.get(f"/bookings/{b.id}/ai-refund",
                   headers={"Authorization": f"Bearer {tok2}"})
    assert r.status_code == 404


def test_ai_refund_booking_not_found(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ir-api-nf")
    u = _user(db, t, "nf@x.com")
    token = _login(client, t.slug, u.email)
    r = client.get("/bookings/does-not-exist/ai-refund",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
