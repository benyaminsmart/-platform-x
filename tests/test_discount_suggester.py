"""Tests for AI Discount Suggester (Phase 25, Step 3)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import discount_suggester


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "disc") -> Tenant:
    t = Tenant(slug=slug, name="Disc Biz", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai, UAE", "rating": 4.7,
                       "reviews_count": 300})
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _user(db: Session, tenant: Tenant, email: str, *, tier: str = "welcome") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U", last_name="X",
        referral_code=email[:10].upper(),
        tier=tier, status="active",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _booking(db: Session, tenant: Tenant, user: User, *, days_ago: int = 5, amount: float = 500) -> Booking:
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
        guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
        total_amount=Decimal(str(amount)), currency="AED",
        status="confirmed", payment_status="paid",
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _stub_ai(content: str):
    def _fake(message, *, history=None, provider_name=None):
        return {"content": content, "provider": "stub", "model": "x", "tokens_used": 0}
    return _fake


# ---------- Basic validation ----------


def test_invalid_language(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        discount_suggester.suggest_discounts(db, tenant=t, language="xx")


def test_max_cap_is_enforced_in_policy() -> None:
    for seg, policy in discount_suggester.POLICY.items():
        assert policy["pct"] <= discount_suggester.MAX_DISCOUNT_PCT, f"{seg} exceeds cap"


# ---------- Empty tenant ----------


def test_empty_tenant_returns_all_fallback(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    out = discount_suggester.suggest_discounts(db, tenant=t)
    # Only 'all' segment remains because there are no customers
    assert len(out["suggestions"]) == 1
    assert out["suggestions"][0]["segment"] == "all"
    assert out["suggestions"][0]["discount_pct"] == 5.0
    assert out["provider"] == "fallback"


# ---------- Real segments ----------


def test_suggests_for_real_segments(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    today = date.today()

    # inactive 90d
    u1 = _user(db, t, "inactive@x.com")
    _booking(db, t, u1, days_ago=200)
    # high value
    u2 = _user(db, t, "high@x.com")
    _booking(db, t, u2, days_ago=5, amount=10000)
    # new
    u3 = _user(db, t, "new@x.com")
    _booking(db, t, u3, days_ago=2)
    # gold tier
    u4 = _user(db, t, "gold@x.com", tier="gold")
    _booking(db, t, u4, days_ago=5)

    out = discount_suggester.suggest_discounts(db, tenant=t)
    segments_offered = {s["segment"] for s in out["suggestions"]}
    assert "inactive_90d" in segments_offered
    assert "high_value" in segments_offered
    assert "new_30d" in segments_offered
    assert "loyalty_gold_plus" in segments_offered


def test_policy_discount_pcts_used(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    u = _user(db, t, "x@x.com")
    _booking(db, t, u, days_ago=200)

    out = discount_suggester.suggest_discounts(db, tenant=t)
    inactive = next(s for s in out["suggestions"] if s["segment"] == "inactive_90d")
    assert inactive["discount_pct"] == 15.0
    assert inactive["duration_days"] == 14


# ---------- Impact estimation ----------


def test_impact_estimate_shape(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    u = _user(db, t, "x@x.com")
    _booking(db, t, u, days_ago=200, amount=1000)

    out = discount_suggester.suggest_discounts(db, tenant=t)
    sug = next(s for s in out["suggestions"] if s["segment"] == "inactive_90d")
    imp = sug["estimated_impact"]
    assert "expected_orders" in imp
    assert "gross_revenue_aed" in imp
    assert "discount_value_aed" in imp
    assert "net_after_discount_aed" in imp
    # Net = gross - discount
    assert abs((imp["gross_revenue_aed"] - imp["discount_value_aed"]) - imp["net_after_discount_aed"]) < 0.02


# ---------- AI rationale ----------


def test_ai_rationale_used_when_available(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _fake(message, *, history=None, provider_name=None):
        return {"content": "AI_RATIONALE_TEXT", "provider": "stub", "model": "x", "tokens_used": 0}
    monkeypatch.setattr(ai_service, "chat", _fake)

    t = _tenant(db)
    u = _user(db, t, "x@x.com")
    _booking(db, t, u, days_ago=200)

    out = discount_suggester.suggest_discounts(db, tenant=t)
    assert out["provider"] == "ai"
    for s in out["suggestions"]:
        assert s["reason"] == "AI_RATIONALE_TEXT"


def test_fallback_rationale_when_ai_fails(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    u = _user(db, t, "x@x.com")
    _booking(db, t, u, days_ago=200)

    out = discount_suggester.suggest_discounts(db, tenant=t)
    sug = next(s for s in out["suggestions"] if s["segment"] == "inactive_90d")
    assert "win back" in sug["reason"].lower() or "15" in sug["reason"]


# ---------- Segment filter ----------


def test_segment_filter(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    u = _user(db, t, "x@x.com")
    _booking(db, t, u, days_ago=200)
    u2 = _user(db, t, "y@x.com")
    _booking(db, t, u2, days_ago=2)

    out = discount_suggester.suggest_discounts(
        db, tenant=t, segment_filter=["inactive_90d"]
    )
    assert len(out["suggestions"]) == 1
    assert out["suggestions"][0]["segment"] == "inactive_90d"


# ---------- Policy cap ----------


def test_pct_is_capped(db: Session, monkeypatch) -> None:
    # Even if policy were tampered, suggest_discounts enforces cap
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    monkeypatch.setitem(discount_suggester.POLICY["inactive_90d"], "pct", 50.0)
    t = _tenant(db)
    u = _user(db, t, "x@x.com")
    _booking(db, t, u, days_ago=200)

    out = discount_suggester.suggest_discounts(db, tenant=t)
    sug = next(s for s in out["suggestions"] if s["segment"] == "inactive_90d")
    assert sug["discount_pct"] <= discount_suggester.MAX_DISCOUNT_PCT
