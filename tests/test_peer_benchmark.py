"""Tests for Deep Peer Benchmark service (Phase 52, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import peer_benchmark as pb


def _tenant(db, slug, typ="hotel", rating=4.5):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": rating, "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, price=500, capacity=2):
    s = Service(tenant_id=t.id, type="room", name=f"R-{t.slug}",
                price=Decimal(str(price)), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _booking(db, t, days_ago=5, nights=1, status="confirmed"):
    from app.models.user import User
    from app.core.security import hash_password
    u_email = f"u-{t.slug}@x.com"
    u = db.query(User).filter(User.email == u_email).one_or_none()
    if u is None:
        u = User(tenant_id=t.id, email=u_email,
                 password_hash=hash_password("Pass1234"),
                 first_name="G", last_name="X",
                 referral_code=u_email[:10].upper(), status="active")
        db.add(u); db.commit(); db.refresh(u)
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci,
                check_out=ci + timedelta(days=nights), guests=1,
                amount=Decimal("500"), discount=Decimal("0"),
                total_amount=Decimal("500"), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_invalid_language(db):
    t = _tenant(db, "pb-lang")
    with pytest.raises(ValueError):
        pb.compute(db, tenant=t, language="xx")


def test_no_peers_returns_fallback(db):
    t = _tenant(db, "pb-solo")
    _svc(db, t)
    out = pb.compute(db, tenant=t)
    assert out["provider"] == "fallback"
    assert "No peer data" in out["summary"]


def test_with_peers_uses_ai(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_SUMMARY", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    me = _tenant(db, "pb-me", rating=4.5)
    p1 = _tenant(db, "pb-p1", rating=4.0)
    p2 = _tenant(db, "pb-p2", rating=4.2)
    _svc(db, me, price=600)
    _svc(db, p1, price=400)
    _svc(db, p2, price=450)

    out = pb.compute(db, tenant=me)
    assert out["provider"] == "ai"
    assert out["summary"] == "AI_SUMMARY"
    metrics = {m["metric"]: m for m in out["metrics"]}
    assert metrics["avg_price"]["self"] == 600.0
    assert metrics["avg_price"]["peer_median"] is not None
    assert metrics["avg_price"]["delta_pct"] > 0


def test_fallback_when_ai_fails(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    me = _tenant(db, "pb-fb-me")
    p1 = _tenant(db, "pb-fb-p1")
    _svc(db, me, price=500)
    _svc(db, p1, price=400)
    out = pb.compute(db, tenant=me)
    assert out["provider"] == "fallback"
    assert "avg_price" in out["summary"]


def test_peer_tenant_identity_never_exposed(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "x", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    me = _tenant(db, "pb-self")
    p1 = _tenant(db, "pb-secret-peer")
    _svc(db, me, price=500)
    _svc(db, p1, price=400)
    out = pb.compute(db, tenant=me)
    import json
    dumped = json.dumps(out)
    assert "pb-secret-peer" not in dumped


def test_different_category_not_included(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "x", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    me = _tenant(db, "pb-cat-me", typ="hotel")
    p_same = _tenant(db, "pb-cat-same", typ="hotel")
    p_diff = _tenant(db, "pb-cat-diff", typ="restaurant")
    _svc(db, me, price=500)
    _svc(db, p_same, price=400)
    _svc(db, p_diff, price=100)
    out = pb.compute(db, tenant=me)
    metrics = {m["metric"]: m for m in out["metrics"]}
    assert metrics["avg_price"]["sample_size"] == 1
    assert metrics["avg_price"]["peer_median"] == 400.0


def test_occupancy_metric_with_capacity(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "x", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    me = _tenant(db, "pb-occ-me")
    p1 = _tenant(db, "pb-occ-p1")
    _svc(db, me, price=500, capacity=1)
    _svc(db, p1, price=400, capacity=1)
    _booking(db, me, days_ago=5, nights=3)
    out = pb.compute(db, tenant=me)
    metrics = {m["metric"]: m for m in out["metrics"]}
    assert metrics["occupancy_30d"]["self"] is not None
    assert metrics["occupancy_30d"]["self"] > 0
