"""Tests for AI Receptionist API (Phase 53, Step 2)."""
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.message import Message
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant_with_owner(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "rating": 4.5, "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    rc = ("OWN" + slug.upper().replace("-", ""))[:30]
    u = User(tenant_id=t.id, email=f"owner@{slug}.com",
             password_hash=hash_password("OwnerPass123"),
             first_name="O", last_name="X", business_role="owner",
             referral_code=rc, status="active")
    db.add(u); db.commit(); db.refresh(u)
    return t, u


def _svc(db, t, price=500, name="Deluxe"):
    s = Service(tenant_id=t.id, type="room", name=name,
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _msg(db, t, thread_id, role, body):
    m = Message(tenant_id=t.id, thread_id=thread_id, sender_role=role, body=body)
    db.add(m); db.commit(); db.refresh(m)
    return m


def _biz_login(client, slug, email):
    r = client.post("/auth/login",
                    json={"email": email, "password": "OwnerPass123"},
                    headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_draft_requires_auth(client: TestClient) -> None:
    r = client.post("/business/api/messages/t1/draft", json={})
    assert r.status_code == 401


def test_draft_ok(client: TestClient, db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_REPLY", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t, owner = _tenant_with_owner(db, "rec-api-1")
    _svc(db, t)
    _msg(db, t, "t1", "user", "How much for a room?")
    token = _biz_login(client, t.slug, owner.email)
    r = client.post("/business/api/messages/t1/draft",
                    json={"language": "en", "tone": "professional"},
                    headers={"Authorization": f"Bearer {token}",
                             "X-Tenant-Slug": t.slug})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reply"] == "AI_REPLY"
    assert body["status"] == "ok"
    assert body["provider"] == "ai"


def test_draft_empty_thread(client: TestClient, db: Session) -> None:
    t, owner = _tenant_with_owner(db, "rec-api-empty")
    token = _biz_login(client, t.slug, owner.email)
    r = client.post("/business/api/messages/missing/draft", json={},
                    headers={"Authorization": f"Bearer {token}",
                             "X-Tenant-Slug": t.slug})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "empty_thread"
    assert body["reply"] == ""


def test_draft_invalid_language(client: TestClient, db: Session) -> None:
    t, owner = _tenant_with_owner(db, "rec-api-lang")
    token = _biz_login(client, t.slug, owner.email)
    r = client.post("/business/api/messages/t1/draft",
                    json={"language": "xx"},
                    headers={"Authorization": f"Bearer {token}",
                             "X-Tenant-Slug": t.slug})
    assert r.status_code == 422


def test_draft_invalid_tone(client: TestClient, db: Session) -> None:
    t, owner = _tenant_with_owner(db, "rec-api-tone")
    token = _biz_login(client, t.slug, owner.email)
    r = client.post("/business/api/messages/t1/draft",
                    json={"tone": "loud"},
                    headers={"Authorization": f"Bearer {token}",
                             "X-Tenant-Slug": t.slug})
    assert r.status_code == 422
