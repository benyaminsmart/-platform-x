"""Tests for the Pricing Coach (Phase 21, Step 2).

All numeric outputs are deterministic and computed in Python.
The AI advice layer is not asserted verbatim (mock provider returns a
deterministic string), only that a non-empty advice string is returned.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai.pricing_coach import (
    analyze_pricing,
    forecast_demand,
    market_insights,
    suggest_pricing,
)


import pytest as _pytest


@_pytest.fixture(autouse=True)
def _fast_ai_stub(monkeypatch):
    """Replace AI service with a fast stub so tests stay <2s total.

    We only assert structure (metrics) + presence of advice string.
    The real AI provider path is covered by test_safe_ai_handles_provider_failure
    and elsewhere in the AI suite.
    """
    from app.services.ai import service as ai_service

    def _fast_chat(message, *, history=None, provider_name=None):
        return {
            "content": "[stub advice]",
            "provider": "stub",
            "model": "stub",
            "tokens_used": 0,
        }

    monkeypatch.setattr(ai_service, "chat", _fast_chat)
    yield



# ---------- Helpers ----------


def _user(db: Session, tenant: Tenant, email: str = "u@x.com") -> User:
    u = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U",
        last_name="One",
        referral_code=email[:10].upper(),
        status="active",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _svc(db: Session, tenant: Tenant, *, typ: str = "room", name: str = "R", price: float = 500) -> Service:
    s = Service(
        tenant_id=tenant.id,
        type=typ,
        name=name,
        price=Decimal(str(price)),
        currency="AED",
        capacity=2,
        attributes={},
        image_urls=[],
        status="active",
        display_order=0,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _bk(
    db: Session,
    tenant: Tenant,
    user: User,
    *,
    ci: date | None = None,
    amount: float = 500,
    status: str = "pending",
    payment_status: str = "pending",
) -> Booking:
    ci = ci or date.today()
    b = Booking(
        tenant_id=tenant.id,
        user_id=user.id,
        booking_type="room",
        service_id=None,
        service_name="R",
        check_in=ci,
        check_out=ci + timedelta(days=1),
        guests=2,
        amount=Decimal(str(amount)),
        discount=Decimal("0"),
        total_amount=Decimal(str(amount)),
        currency="AED",
        status=status,
        payment_status=payment_status,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _make_peer(db: Session, slug: str, price: float, status: str = "active") -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status=status, config={})
    db.add(t)
    db.commit()
    db.refresh(t)
    _svc(db, t, typ="room", name=slug, price=price)
    return t


# ---------- analyze_pricing ----------


def test_analyze_pricing_empty_tenant(db: Session, sample_tenant: Tenant) -> None:
    out = analyze_pricing(db, sample_tenant)
    m = out["metrics"]
    assert m["dominant_type"] is None
    assert m["active_services"] == 0
    assert m["pricing_by_type"] == {}
    assert isinstance(out["advice"], str)
    assert out["advice"]  # non-empty


def test_analyze_pricing_with_data(db: Session, sample_tenant: Tenant) -> None:
    _svc(db, sample_tenant, typ="room", name="A", price=200)
    _svc(db, sample_tenant, typ="room", name="B", price=400)
    out = analyze_pricing(db, sample_tenant)
    m = out["metrics"]
    assert m["dominant_type"] == "room"
    assert m["active_services"] == 2
    assert m["pricing_by_type"]["room"]["avg"] == 300.0
    assert out["advice"]


def test_analyze_pricing_position_below_market(db: Session, sample_tenant: Tenant) -> None:
    # own avg = 200
    _svc(db, sample_tenant, typ="room", name="A", price=200)
    # peers avg = 500
    _make_peer(db, "p1", 500)
    _make_peer(db, "p2", 500)

    out = analyze_pricing(db, sample_tenant)
    positions = out["metrics"]["position_by_type"]
    assert positions.get("room") == "below_market"
    assert out["metrics"]["benchmark"]["cohort_size"] == 2


def test_analyze_pricing_position_above_market(db: Session, sample_tenant: Tenant) -> None:
    _svc(db, sample_tenant, typ="room", name="A", price=1000)
    _make_peer(db, "p1", 400)
    _make_peer(db, "p2", 400)

    out = analyze_pricing(db, sample_tenant)
    assert out["metrics"]["position_by_type"].get("room") == "above_market"


def test_analyze_pricing_position_at_market(db: Session, sample_tenant: Tenant) -> None:
    _svc(db, sample_tenant, typ="room", name="A", price=500)
    _make_peer(db, "p1", 500)
    _make_peer(db, "p2", 505)

    out = analyze_pricing(db, sample_tenant)
    # own 500 vs cohort 502.5 → -0.5% → at_market
    assert out["metrics"]["position_by_type"].get("room") == "at_market"


# ---------- suggest_pricing ----------


def test_suggest_pricing_no_peers(db: Session, sample_tenant: Tenant) -> None:
    _svc(db, sample_tenant, typ="room", name="A", price=300)
    out = suggest_pricing(db, sample_tenant)
    sugg = out["metrics"]["suggestions"]
    assert len(sugg) == 1
    assert sugg[0]["type"] is None
    assert "not enough peer data" in sugg[0]["note"].lower()
    assert out["advice"]


def test_suggest_pricing_below_market_suggests_increase(db: Session, sample_tenant: Tenant) -> None:
    _svc(db, sample_tenant, typ="room", name="A", price=200)
    _make_peer(db, "p1", 500)
    _make_peer(db, "p2", 500)

    out = suggest_pricing(db, sample_tenant)
    s = out["metrics"]["suggestions"][0]
    assert s["type"] == "room"
    assert s["suggested_change_pct"] > 0
    assert s["suggested_change_pct"] <= 5.0
    assert s["suggested_new_avg_aed"] > s["current_avg_aed"]
    assert "below" in s["reason"].lower()


def test_suggest_pricing_above_market_suggests_decrease(db: Session, sample_tenant: Tenant) -> None:
    _svc(db, sample_tenant, typ="room", name="A", price=1000)
    _make_peer(db, "p1", 400)
    _make_peer(db, "p2", 400)

    out = suggest_pricing(db, sample_tenant)
    s = out["metrics"]["suggestions"][0]
    assert s["suggested_change_pct"] < 0
    assert s["suggested_new_avg_aed"] < s["current_avg_aed"]


def test_suggest_pricing_at_market_hold(db: Session, sample_tenant: Tenant) -> None:
    _svc(db, sample_tenant, typ="room", name="A", price=500)
    _make_peer(db, "p1", 500)
    _make_peer(db, "p2", 500)

    out = suggest_pricing(db, sample_tenant)
    s = out["metrics"]["suggestions"][0]
    assert s["suggested_change_pct"] == 0.0
    assert "hold" in s["reason"].lower() or "market" in s["reason"].lower()


def test_suggest_pricing_at_market_negative_trend_suggests_reduction(
    db: Session, sample_tenant: Tenant
) -> None:
    _svc(db, sample_tenant, typ="room", name="A", price=500)
    _make_peer(db, "p1", 500)
    _make_peer(db, "p2", 500)

    u = _user(db, sample_tenant)
    today = date.today()
    # last 30 days: 1 booking; prev 30: 5 bookings → negative growth
    _bk(db, sample_tenant, u, ci=today - timedelta(days=5))
    for i in range(5):
        _bk(db, sample_tenant, u, ci=today - timedelta(days=40 + i))

    out = suggest_pricing(db, sample_tenant)
    s = out["metrics"]["suggestions"][0]
    assert s["suggested_change_pct"] == -3.0
    assert "dropped" in s["reason"].lower() or "reduction" in s["reason"].lower() or "recover" in s["reason"].lower()


def test_suggest_pricing_at_market_positive_trend_suggests_increase(
    db: Session, sample_tenant: Tenant
) -> None:
    _svc(db, sample_tenant, typ="room", name="A", price=500)
    _make_peer(db, "p1", 500)
    _make_peer(db, "p2", 500)

    u = _user(db, sample_tenant)
    today = date.today()
    # last 30: 6; prev 30: 1 → positive growth
    for i in range(6):
        _bk(db, sample_tenant, u, ci=today - timedelta(days=5 + i))
    _bk(db, sample_tenant, u, ci=today - timedelta(days=45))

    out = suggest_pricing(db, sample_tenant)
    s = out["metrics"]["suggestions"][0]
    assert s["suggested_change_pct"] == 3.0
    assert "grew" in s["reason"].lower() or "increase" in s["reason"].lower() or "value" in s["reason"].lower()


# ---------- forecast_demand ----------


def test_forecast_demand_empty_tenant(db: Session, sample_tenant: Tenant) -> None:
    out = forecast_demand(db, sample_tenant, days=30)
    m = out["metrics"]
    assert m["days"] == 30
    assert m["weekly_avg_last_30d"] == 0.0
    assert m["expected_bookings"] == 0.0
    assert m["low_bookings"] == 0.0
    assert m["high_bookings"] == 0.0
    assert out["advice"]


def test_forecast_demand_with_history(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant)
    today = date.today()
    # 7 bookings in last 30 days → weekly avg ≈ 1.633
    for i in range(7):
        _bk(db, sample_tenant, u, ci=today - timedelta(days=3 + i))

    out = forecast_demand(db, sample_tenant, days=30)
    m = out["metrics"]
    assert m["weekly_avg_last_30d"] > 0
    assert m["expected_bookings"] > 0
    assert m["low_bookings"] < m["expected_bookings"] < m["high_bookings"]


def test_forecast_demand_days_clamped(db: Session, sample_tenant: Tenant) -> None:
    out_low = forecast_demand(db, sample_tenant, days=1)
    assert out_low["metrics"]["days"] == 7
    out_high = forecast_demand(db, sample_tenant, days=500)
    assert out_high["metrics"]["days"] == 90


# ---------- market_insights ----------


def test_market_insights_empty(db: Session, sample_tenant: Tenant) -> None:
    out = market_insights(db, sample_tenant)
    m = out["metrics"]
    assert m["dominant_type"] is None
    assert m["cohort_size"] == 0
    assert m["cohort_avg_price_aed"] is None
    assert out["advice"]


def test_market_insights_with_peers(db: Session, sample_tenant: Tenant) -> None:
    _svc(db, sample_tenant, typ="room", name="A", price=300)
    _make_peer(db, "p1", 500)
    _make_peer(db, "p2", 500)

    out = market_insights(db, sample_tenant)
    m = out["metrics"]
    assert m["dominant_type"] == "room"
    assert m["cohort_size"] == 2
    assert m["cohort_avg_price_aed"] == 500.0
    assert m["your_avg_price_aed"] == 300.0
    assert m["your_position_pct"] == -40.0
    # No peer identity leak
    text = str(m) + out["advice"]
    assert "p1" not in text
    assert "p2" not in text


# ---------- AI wrapper resilience ----------


def test_safe_ai_handles_provider_failure(db: Session, sample_tenant: Tenant, monkeypatch) -> None:
    """If AI raises, _safe_ai must return a fallback and not bubble up."""
    from app.services.ai import pricing_coach as pc
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("simulated AI failure")

    monkeypatch.setattr(ai_service, "chat", _boom)

    out = pc.analyze_pricing(db, sample_tenant)
    assert out["advice"] == "AI advice unavailable right now. The metrics above are live."
    assert "metrics" in out
