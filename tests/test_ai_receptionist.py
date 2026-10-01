"""Tests for AI Receptionist service (Phase 53, Step 1)."""
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.message import Message
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import receptionist as rec


def _tenant(db, slug, typ="hotel"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": 4.5, "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, price=500, typ="room", name=None):
    s = Service(tenant_id=t.id, type=typ, name=name or f"{typ}-{t.slug}",
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


def _msg(db, t, thread_id, role, body):
    m = Message(tenant_id=t.id, thread_id=thread_id, sender_role=role, body=body)
    db.add(m); db.commit(); db.refresh(m)
    return m


def test_invalid_language(db):
    t = _tenant(db, "rec-lang")
    with pytest.raises(ValueError):
        rec.draft_reply(db, tenant=t, thread_id="x", language="xx")


def test_invalid_tone(db):
    t = _tenant(db, "rec-tone")
    with pytest.raises(ValueError):
        rec.draft_reply(db, tenant=t, thread_id="x", tone="loud")


def test_empty_thread(db):
    t = _tenant(db, "rec-empty")
    out = rec.draft_reply(db, tenant=t, thread_id="missing")
    assert out["status"] == "empty_thread"
    assert out["provider"] == "fallback"
    assert out["reply"] == ""


def test_no_guest_message(db):
    t = _tenant(db, "rec-noguest")
    _msg(db, t, "t1", "business", "Hello from us")
    out = rec.draft_reply(db, tenant=t, thread_id="t1")
    assert out["status"] == "no_guest_message"


def test_ai_reply_grounded(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_REPLY", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "rec-ai")
    _svc(db, t, price=500, name="Deluxe Room")
    _svc(db, t, price=800, name="Suite")
    _msg(db, t, "t1", "user", "How much is a room next weekend?")
    out = rec.draft_reply(db, tenant=t, thread_id="t1")
    assert out["status"] == "ok"
    assert out["provider"] == "ai"
    assert out["reply"] == "AI_REPLY"


def test_fallback_when_ai_fails(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    t = _tenant(db, "rec-fb")
    _svc(db, t, price=500, name="Deluxe Room")
    _msg(db, t, "t1", "user", "Hello?")
    out = rec.draft_reply(db, tenant=t, thread_id="t1")
    assert out["status"] == "ok"
    assert out["provider"] == "fallback"
    assert "Thank you for contacting" in out["reply"]


def test_fallback_with_no_services(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    t = _tenant(db, "rec-nosvc")
    _msg(db, t, "t1", "user", "Hi")
    out = rec.draft_reply(db, tenant=t, thread_id="t1")
    assert out["status"] == "ok"
    assert "will reply" in out["reply"] or "received your message" in out["reply"]


def test_last_guest_message_used_for_anchor(db, monkeypatch):
    captured = {}
    from app.services.ai import service as ai_service
    def _spy(prompt, **kw):
        captured["prompt"] = prompt
        return {"content": "ok", "provider": "x", "model": "x", "tokens_used": 0}
    monkeypatch.setattr(ai_service, "chat", _spy)
    t = _tenant(db, "rec-anchor")
    _svc(db, t, price=500)
    _msg(db, t, "t1", "user", "First question")
    _msg(db, t, "t1", "business", "We replied")
    _msg(db, t, "t1", "user", "Second question")
    rec.draft_reply(db, tenant=t, thread_id="t1")
    assert "Second question" in captured["prompt"]
    assert "First question" in captured["prompt"]
