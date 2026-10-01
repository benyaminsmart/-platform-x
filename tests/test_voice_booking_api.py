"""Tests for AI Voice Booking API (Phase 64, Step 2)."""
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug, typ="hotel", location="Dubai"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": 4.5, "location": location})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, name="Room", price=500):
    s = Service(tenant_id=t.id, type="room", name=name,
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _login(client, slug, email):
    r = client.post("/auth/login", json={"email": email, "password": "Pass1234"},
                    headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_voice_requires_auth(client: TestClient) -> None:
    r = client.post("/account/api/ai/voice", json={"transcript": "hello"})
    assert r.status_code == 401


def test_voice_ok(client: TestClient, db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_REPLY", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "vb-api-1")
    u = _user(db, t)
    _svc(db, t)
    token = _login(client, t.slug, u.email)
    r = client.post("/account/api/ai/voice",
                    json={"transcript": "Book a hotel in Dubai next weekend for 2"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["reply"] == "AI_REPLY"
    assert body["intent"]["category"] == "hotels"
    assert body["intent"]["city"] == "Dubai"


def test_voice_unrecognized(client: TestClient, db: Session) -> None:
    t = _tenant(db, "vb-api-unrec")
    u = _user(db, t, "unrec@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/account/api/ai/voice",
                    json={"transcript": "blah blah nothing"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "unrecognized"


def test_voice_invalid_language(client: TestClient, db: Session) -> None:
    t = _tenant(db, "vb-api-lang")
    u = _user(db, t, "lang@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/account/api/ai/voice",
                    json={"transcript": "hotel in Dubai", "language": "xx"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_voice_empty_transcript_rejected(client: TestClient, db: Session) -> None:
    t = _tenant(db, "vb-api-empty")
    u = _user(db, t, "empty@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/account/api/ai/voice",
                    json={"transcript": ""},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422
