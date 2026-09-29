"""Integration tests: Pricing Rules applied during booking creation.

Covers Phase 22, Step 4:
- Legacy behavior preserved when apply_pricing_rules=False (default)
- Rules applied server-side when apply_pricing_rules=True
- Amount uses server-computed service price, not client value
- Positive delta (increase) -> discount stays 0
- Negative delta (decrease) -> discount reflects reduction
- Audit rows created for each applied rule
- Service from another tenant ignored (falls back to legacy)
- service_id null -> legacy
"""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.pricing_rule import PricingRuleApplication
from app.models.service import Service
from app.models.tenant import Tenant


# ---------- Helpers ----------


def _svc(db: Session, tenant: Tenant, *, price: float = 500, name: str = "R") -> Service:
    s = Service(
        tenant_id=tenant.id,
        type="room",
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


def _rule_custom_percent(db: Session, tenant: Tenant, *, value: float, priority: int = 100) -> None:
    from app.models.pricing_rule import PricingRule
    r = PricingRule(
        tenant_id=tenant.id,
        name=f"rule {value}%",
        rule_type="custom",
        conditions={},
        action={"type": "percent", "value": value},
        priority=priority,
        active=True,
        service_ids=[],
    )
    db.add(r)
    db.commit()


def _rule_weekend_percent(db: Session, tenant: Tenant, *, value: float) -> None:
    from app.models.pricing_rule import PricingRule
    r = PricingRule(
        tenant_id=tenant.id,
        name="weekend rule",
        rule_type="weekend",
        conditions={"days_of_week": [5, 6]},
        action={"type": "percent", "value": value},
        priority=100,
        active=True,
        service_ids=[],
    )
    db.add(r)
    db.commit()


def _guest_token(client: TestClient, slug: str, email: str = "g@x.com") -> dict:
    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "GuestPass123",
            "first_name": "G",
            "last_name": "U",
        },
        headers={"X-Tenant-Slug": slug},
    )
    return {"X-Tenant-Slug": slug, "Authorization": f"Bearer {reg.json()['access_token']}"}


def _payload(service_id: str | None, *, amount: str = "500.00", apply: bool = False, check_in: str = "2026-10-01") -> dict:
    return {
        "booking_type": "room",
        "service_id": service_id,
        "service_name": "R",
        "check_in": check_in,
        "guests": 1,
        "amount": amount,
        "apply_pricing_rules": apply,
    }


# ---------- Legacy behavior ----------


def test_legacy_default_no_rules_applied(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    s = _svc(db, sample_tenant, price=500)
    _rule_custom_percent(db, sample_tenant, value=50)  # would apply if used
    h = _guest_token(client, sample_tenant.slug)

    r = client.post("/bookings", json=_payload(s.id, amount="500.00", apply=False), headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    # Client-supplied amount respected
    assert body["amount"] == "500.00"
    assert body["discount"] == "0.00"
    assert body["total_amount"] == "500.00"
    # No audit rows
    assert db.query(PricingRuleApplication).count() == 0


def test_legacy_when_no_service_id(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _rule_custom_percent(db, sample_tenant, value=50)
    h = _guest_token(client, sample_tenant.slug)

    r = client.post("/bookings", json=_payload(None, amount="500.00", apply=True), headers=h)
    assert r.status_code == 201
    body = r.json()
    # No service to apply rules on -> legacy
    assert body["amount"] == "500.00"
    assert body["total_amount"] == "500.00"
    assert db.query(PricingRuleApplication).count() == 0


def test_cross_tenant_service_ignored(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    # Tenant B owns the service, but user books with tenant A's header
    tb = Tenant(slug="other-b", name="B", tier="starter", status="active", config={})
    db.add(tb)
    db.commit()
    db.refresh(tb)
    s_b = _svc(db, tb, price=500)

    # Rule attached to tenant A (should NOT be applied to B's service)
    _rule_custom_percent(db, sample_tenant, value=50)

    h = _guest_token(client, sample_tenant.slug)
    r = client.post("/bookings", json=_payload(s_b.id, amount="500.00", apply=True), headers=h)
    assert r.status_code == 201
    body = r.json()
    # No rules applied because service belongs to another tenant
    assert body["amount"] == "500.00"
    assert body["total_amount"] == "500.00"
    assert db.query(PricingRuleApplication).count() == 0


# ---------- Rules applied ----------


def test_rules_increase_price_discount_zero(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    s = _svc(db, sample_tenant, price=500)
    _rule_custom_percent(db, sample_tenant, value=20)  # +20% -> 600

    h = _guest_token(client, sample_tenant.slug)
    r = client.post("/bookings", json=_payload(s.id, amount="999.00", apply=True), headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    # amount replaced with service base price (server-computed)
    assert body["amount"] == "500.00"
    # increase -> discount stays 0
    assert body["discount"] == "0.00"
    assert body["total_amount"] == "600.00"
    # Audit row created
    apps = db.query(PricingRuleApplication).all()
    assert len(apps) == 1
    assert apps[0].original_price == "500.00"
    assert apps[0].adjusted_price == "600.00"
    assert apps[0].delta_amount == "100.00"
    assert apps[0].booking_id == body["id"]


def test_rules_decrease_price_discount_reflects_reduction(
    client: TestClient, sample_tenant: Tenant, db: Session
) -> None:
    s = _svc(db, sample_tenant, price=500)
    _rule_custom_percent(db, sample_tenant, value=-20)  # -20% -> 400

    h = _guest_token(client, sample_tenant.slug)
    r = client.post("/bookings", json=_payload(s.id, amount="999.00", apply=True), headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["amount"] == "500.00"
    # decrease -> discount = 100, total = 400
    assert body["discount"] == "100.00"
    assert body["total_amount"] == "400.00"
    apps = db.query(PricingRuleApplication).all()
    assert len(apps) == 1
    assert apps[0].delta_amount == "-100.00"


def test_stacking_creates_audit_per_rule(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    s = _svc(db, sample_tenant, price=500)
    _rule_custom_percent(db, sample_tenant, value=10, priority=50)   # +10% -> 550
    _rule_custom_percent(db, sample_tenant, value=-5, priority=100)  # -5% of 550 = -27.50 -> 522.50

    h = _guest_token(client, sample_tenant.slug)
    r = client.post("/bookings", json=_payload(s.id, amount="500.00", apply=True), headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["amount"] == "500.00"
    assert body["total_amount"] == "522.50"
    # discount = base - final = 500 - 522.50 = -22.50 -> negative; we set it to 0 when increase
    assert body["discount"] == "0.00"
    apps = db.query(PricingRuleApplication).all()
    assert len(apps) == 2


def test_weekend_rule_applies_on_saturday(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    s = _svc(db, sample_tenant, price=500)
    _rule_weekend_percent(db, sample_tenant, value=20)
    h = _guest_token(client, sample_tenant.slug)

    # 2026-10-03 is a Saturday
    r = client.post("/bookings", json=_payload(s.id, apply=True, check_in="2026-10-03"), headers=h)
    assert r.status_code == 201
    assert r.json()["total_amount"] == "600.00"

    # 2026-10-01 is a Thursday -> rule ignored
    r = client.post("/bookings", json=_payload(s.id, apply=True, check_in="2026-10-01"), headers=h)
    assert r.status_code == 201
    assert r.json()["total_amount"] == "500.00"


def test_negative_price_floored(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    s = _svc(db, sample_tenant, price=500)
    from app.models.pricing_rule import PricingRule
    r = PricingRule(
        tenant_id=sample_tenant.id,
        name="crazy discount",
        rule_type="custom",
        conditions={},
        action={"type": "fixed", "value": -1000},
        priority=100,
        active=True,
        service_ids=[],
    )
    db.add(r)
    db.commit()

    h = _guest_token(client, sample_tenant.slug)
    resp = client.post("/bookings", json=_payload(s.id, apply=True), headers=h)
    assert resp.status_code == 201
    body = resp.json()
    # Never below 0
    assert body["total_amount"] == "0.00"
