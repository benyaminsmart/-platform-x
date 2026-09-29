"""Tests for Revenue Forecast service (Phase 26, Step 3)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services import revenue_forecast


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "rf") -> Tenant:
    t = Tenant(slug=slug, name="RF", tier="starter", status="active", config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db: Session, tenant: Tenant, email: str = "u@x.com") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U", last_name="X",
        referral_code=email[:10].upper(),
        status="active",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(
    db: Session, tenant: Tenant, user: User, *,
    check_in: date, amount: float = 500, paid: bool = True, status: str = "confirmed",
) -> Booking:
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_name="R", check_in=check_in, check_out=check_in + timedelta(days=1),
        guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
        total_amount=Decimal(str(amount)), currency="AED",
        status=status,
        payment_status="paid" if paid else "pending",
    )
    db.add(b); db.commit(); db.refresh(b)
    return b


# ---------- Empty ----------


def test_forecast_empty(db: Session) -> None:
    t = _tenant(db)
    out = revenue_forecast.forecast_revenue(db, t, days=30, today=date(2026, 9, 15))
    m = out
    assert m["daily_avg_last_30d"] == 0.0
    assert m["expected_revenue"] == 0.0
    assert m["note"]


def test_forecast_with_recent_paid_bookings(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    today = date(2026, 9, 15)

    # 30 days: 10 bookings of 1000 each -> 10,000 revenue -> avg 333.33/day
    for i in range(10):
        _booking(db, t, u, check_in=today - timedelta(days=i + 1), amount=1000)

    out = revenue_forecast.forecast_revenue(db, t, days=30, today=today)
    # 10 bookings / 30 days = 333.33
    assert abs(out["daily_avg_last_30d"] - (10000 / 30)) < 0.01
    assert out["revenue_last_30d"] == 10000.0
    # No prior revenue -> no growth
    assert out["raw_growth_pct"] == 0.0
    assert out["growth_factor_applied"] == 1.0
    # Expected ~ (0.7 * 333.33 + 0.3 * 10000/90) * 30
    expected_avg = 0.7 * (10000 / 30) + 0.3 * (10000 / 90)
    expected_rev = expected_avg * 30
    assert abs(out["expected_revenue"] - expected_rev) < 0.1


def test_forecast_growth_positive(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    today = date(2026, 9, 15)

    # Prior 30: 1 booking of 1000 (1000/30 days)
    _booking(db, t, u, check_in=today - timedelta(days=45), amount=1000)
    # Current 30: 5 bookings of 1000 each (5000/30 days)
    for i in range(5):
        _booking(db, t, u, check_in=today - timedelta(days=i + 1), amount=1000)

    out = revenue_forecast.forecast_revenue(db, t, days=30, today=today)
    assert out["revenue_prev_30d"] == 1000.0
    assert out["revenue_last_30d"] == 5000.0
    # growth = (5000-1000)/1000 = 400% -> clamped to 50% -> factor 1.5
    assert out["raw_growth_pct"] == 400.0
    assert out["growth_factor_applied"] == 1.5


def test_forecast_growth_negative_clamped(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    today = date(2026, 9, 15)

    # Prior: 10,000
    for i in range(10):
        _booking(db, t, u, check_in=today - timedelta(days=45 + i), amount=1000)
    # Current: 0
    out = revenue_forecast.forecast_revenue(db, t, days=30, today=today)
    assert out["revenue_last_30d"] == 0.0
    assert out["revenue_prev_30d"] == 10000.0
    # growth = -100% -> clamped to -50% -> factor 0.5
    assert out["growth_factor_applied"] == 0.5


def test_forecast_only_paid_counts(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    today = date(2026, 9, 15)
    _booking(db, t, u, check_in=today - timedelta(days=5), amount=1000, paid=False)
    _booking(db, t, u, check_in=today - timedelta(days=5), amount=1000, paid=True)

    out = revenue_forecast.forecast_revenue(db, t, days=30, today=today)
    assert out["revenue_last_30d"] == 1000.0


def test_forecast_cancelled_excluded(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    today = date(2026, 9, 15)
    _booking(db, t, u, check_in=today - timedelta(days=5), amount=1000, status="cancelled")
    out = revenue_forecast.forecast_revenue(db, t, days=30, today=today)
    assert out["revenue_last_30d"] == 0.0


def test_forecast_days_clamped(db: Session) -> None:
    t = _tenant(db)
    out_lo = revenue_forecast.forecast_revenue(db, t, days=1, today=date(2026, 9, 15))
    assert out_lo["forecast_days"] == 7
    out_hi = revenue_forecast.forecast_revenue(db, t, days=9999, today=date(2026, 9, 15))
    assert out_hi["forecast_days"] == 180


def test_forecast_band_symmetric(db: Session) -> None:
    t = _tenant(db)
    u = _user(db, t)
    today = date(2026, 9, 15)
    for i in range(5):
        _booking(db, t, u, check_in=today - timedelta(days=i + 1), amount=1000)
    out = revenue_forecast.forecast_revenue(db, t, days=30, today=today)
    assert out["low_revenue"] == round(out["expected_revenue"] * 0.8, 2)
    assert out["high_revenue"] == round(out["expected_revenue"] * 1.2, 2)


# ---------- With advice ----------


def test_forecast_with_advice_ai(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _fake(message, *, history=None, provider_name=None):
        return {"content": "AI_FORECAST_ADVICE", "provider": "stub", "model": "x", "tokens_used": 0}
    monkeypatch.setattr(ai_service, "chat", _fake)

    t = _tenant(db)
    out = revenue_forecast.forecast_with_advice(db, t, days=30, today=date(2026, 9, 15))
    assert out["advice"] == "AI_FORECAST_ADVICE"
    assert "metrics" in out


def test_forecast_with_advice_fallback(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    u = _user(db, t)
    today = date(2026, 9, 15)
    for i in range(3):
        _booking(db, t, u, check_in=today - timedelta(days=i + 1), amount=1000)

    out = revenue_forecast.forecast_with_advice(db, t, days=30, today=today)
    assert "AED" in out["advice"]
    assert "forecast" in out["advice"].lower() or "expect" in out["advice"].lower()


def test_forecast_fallback_empty(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    out = revenue_forecast.forecast_with_advice(db, t, days=30, today=date(2026, 9, 15))
    assert out["advice"]
    assert "not enough" in out["advice"].lower() or "no paid" in out["advice"].lower()


# ---------- Cross-tenant ----------


def test_cross_tenant_isolation(db: Session) -> None:
    t1 = _tenant(db, "rf-a")
    t2 = _tenant(db, "rf-b")
    u1 = _user(db, t1, "a@x.com")
    u2 = _user(db, t2, "b@x.com")
    today = date(2026, 9, 15)

    _booking(db, t1, u1, check_in=today - timedelta(days=5), amount=1000)
    _booking(db, t2, u2, check_in=today - timedelta(days=5), amount=5000)

    o1 = revenue_forecast.forecast_revenue(db, t1, days=30, today=today)
    o2 = revenue_forecast.forecast_revenue(db, t2, days=30, today=today)
    assert o1["revenue_last_30d"] == 1000.0
    assert o2["revenue_last_30d"] == 5000.0
