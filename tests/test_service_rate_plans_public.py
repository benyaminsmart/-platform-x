"""Tests for public service rate plans endpoint (Phase 37, Step 5)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.rate_plan import RatePlan
from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name="R",
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _plan(db, t, s, code, modifier=15, active=True):
    rp = RatePlan(tenant_id=t.id, service_id=s.id, name=code.upper(), code=code,
                  price_modifier_type="percent",
                  price_modifier_value=Decimal(str(modifier)),
                  meal_plan="none", refundable=True, active=active)
    db.add(rp); db.commit(); db.refresh(rp)
    return rp


def test_public_list_rate_plans(client, db):
    t = _tenant(db, "srp-pub")
    s = _svc(db, t)
    _plan(db, t, s, "bb", 15)
    _plan(db, t, s, "ro", 0)
    r = client.get(f"/services/{s.id}/rate-plans", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["code"] == "ro"
    assert body[1]["code"] == "bb"


def test_public_excludes_inactive(client, db):
    t = _tenant(db, "srp-inactive")
    s = _svc(db, t)
    _plan(db, t, s, "on", 10, active=True)
    _plan(db, t, s, "off", 20, active=False)
    r = client.get(f"/services/{s.id}/rate-plans", headers={"X-Tenant-Slug": t.slug})
    assert len(r.json()) == 1


def test_public_empty(client, db):
    t = _tenant(db, "srp-empty")
    s = _svc(db, t)
    r = client.get(f"/services/{s.id}/rate-plans", headers={"X-Tenant-Slug": t.slug})
    assert r.json() == []
