"""Tests for Reward Eligibility + Calculation (Phase 76, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.reward_rule import RewardRule
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_eligibility as re


def _tenant(db, slug, typ="hotel"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="u@x.com", tier="EXPLORER"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", tier=tier,
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _rule(db, category, rate="0.0100", max_amt="200.00", min_amt="100.00", enabled=True):
    existing = db.query(RewardRule).filter(RewardRule.category == category).one_or_none()
    if existing:
        existing.platform_reward_rate = Decimal(rate)
        existing.max_reward_amount = Decimal(max_amt)
        existing.min_transaction_amount = Decimal(min_amt)
        existing.enabled = enabled
        db.commit()
        return existing
    r = RewardRule(category=category, platform_reward_rate=Decimal(rate),
                   max_reward_amount=Decimal(max_amt),
                   min_transaction_amount=Decimal(min_amt),
                   enabled=enabled)
    db.add(r); db.commit(); db.refresh(r)
    return r


def _booking(db, t, u, amount=1000, status="confirmed", payment_status="paid",
             btype="room"):
    ci = date.today() + timedelta(days=30)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type=btype,
                service_name="X", check_in=ci,
                check_out=ci + timedelta(days=1), guests=1,
                amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status=status, payment_status=payment_status)
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_category_resolution_from_booking_type(db):
    t = _tenant(db, "re-elig-1")
    u = _user(db, t)
    b = _booking(db, t, u, btype="room")
    assert re.category_for(tenant=t, booking=b) == "HOTEL"
    b2 = _booking(db, t, u, btype="table")
    assert re.category_for(tenant=t, booking=b2) == "DINING"


def test_category_resolution_from_tenant(db):
    t = _tenant(db, "re-elig-2", typ="restaurant")
    assert re.category_for(tenant=t) == "DINING"


def test_not_qualifying_when_cancelled(db):
    t = _tenant(db, "re-nq-1")
    u = _user(db, t)
    _rule(db, "HOTEL")
    b = _booking(db, t, u, status="cancelled")
    out = re.is_qualifying_transaction(db, tenant=t, user=u, booking=b)
    assert out.qualifies is False
    assert out.reason == "booking_cancelled"


def test_not_qualifying_when_unpaid(db):
    t = _tenant(db, "re-nq-2")
    u = _user(db, t)
    _rule(db, "HOTEL")
    b = _booking(db, t, u, payment_status="pending")
    out = re.is_qualifying_transaction(db, tenant=t, user=u, booking=b)
    assert out.qualifies is False
    assert out.reason == "not_paid"


def test_not_qualifying_below_minimum(db):
    t = _tenant(db, "re-nq-3")
    u = _user(db, t)
    _rule(db, "HOTEL", min_amt="500.00")
    b = _booking(db, t, u, amount=100)
    out = re.is_qualifying_transaction(db, tenant=t, user=u, booking=b)
    assert out.qualifies is False
    assert out.reason == "below_minimum"


def test_not_qualifying_when_payment_reversed(db):
    t = _tenant(db, "re-nq-4")
    u = _user(db, t)
    _rule(db, "HOTEL")
    b = _booking(db, t, u, amount=1000)
    p = Payment(tenant_id=t.id, user_id=u.id, booking_id=b.id,
                amount=Decimal("1000"), currency="AED", provider="mock",
                provider_reference="ref-1", status="refunded", method="mock")
    db.add(p); db.commit()
    out = re.is_qualifying_transaction(db, tenant=t, user=u, booking=b, payment=p)
    assert out.qualifies is False
    assert out.reason == "payment_reversed"


def test_base_reward_1000_at_1pct(db):
    t = _tenant(db, "re-calc-1")
    u = _user(db, t, "calc1@x.com", tier="EXPLORER")
    _rule(db, "HOTEL", rate="0.0100", max_amt="500.00")
    b = _booking(db, t, u, amount=1000)
    out = re.calculate_reward(db, tenant=t, user=u, booking=b)
    assert out.qualifies is True
    assert out.base_reward == Decimal("10.00")
    assert out.tier_bonus == Decimal("0.00")  # EXPLORER multiplier is 1.00
    assert out.final_reward == Decimal("10.00")


def test_tier_multiplier_applied_as_bonus(db):
    t = _tenant(db, "re-calc-2")
    u = _user(db, t, "calc2@x.com", tier="VIP")
    _rule(db, "HOTEL", rate="0.0100", max_amt="500.00")
    b = _booking(db, t, u, amount=1000)
    out = re.calculate_reward(db, tenant=t, user=u, booking=b)
    # base = 10, VIP mult = 2.0 → bonus = 10, total = 20
    assert out.base_reward == Decimal("10.00")
    assert out.tier_bonus == Decimal("10.00")
    assert out.final_reward == Decimal("20.00")


def test_category_cap_applies(db):
    t = _tenant(db, "re-calc-3")
    u = _user(db, t, "calc3@x.com", tier="VIP")
    _rule(db, "HOTEL", rate="0.10", max_amt="5.00")  # extreme rate, tiny cap
    b = _booking(db, t, u, amount=1000)  # base 100, bonus 100, cap 5
    out = re.calculate_reward(db, tenant=t, user=u, booking=b)
    assert out.cap_applied is True
    assert out.final_reward == Decimal("5.00")


def test_economic_cap_applies(db):
    t = _tenant(db, "re-calc-4")
    u = _user(db, t, "calc4@x.com", tier="EXPLORER")
    # rate 0.02 → base 20 on 1000; commission 60; budget 30; no cap.
    # To force economic cap: rate 0.05 → base 50 > 30.
    _rule(db, "HOTEL", rate="0.0500", max_amt="500.00")
    b = _booking(db, t, u, amount=1000)
    out = re.calculate_reward(db, tenant=t, user=u, booking=b)
    assert out.economic_cap_applied is True
    assert out.final_reward == Decimal("30.00")  # 60 * 0.50


def test_not_qualifying_returns_zero_reward(db):
    t = _tenant(db, "re-calc-5")
    u = _user(db, t, "calc5@x.com")
    _rule(db, "HOTEL")
    b = _booking(db, t, u, status="cancelled")
    out = re.calculate_reward(db, tenant=t, user=u, booking=b)
    assert out.qualifies is False
    assert out.final_reward == Decimal("0.00")
    assert out.reason == "booking_cancelled"


def test_disabled_category(db):
    t = _tenant(db, "re-calc-6")
    u = _user(db, t, "calc6@x.com")
    _rule(db, "HOTEL", enabled=False)
    b = _booking(db, t, u, amount=1000)
    out = re.is_qualifying_transaction(db, tenant=t, user=u, booking=b)
    assert out.qualifies is False
    assert out.reason == "category_disabled"
