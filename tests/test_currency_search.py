"""Tests: currency conversion in search (Phase 30, Step 6b)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, tenant, price=367):
    s = Service(tenant_id=tenant.id, type="room", name="R",
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_search_no_currency_returns_aed(client, db):
    t = _tenant(db, "cur-aed")
    _svc(db, t, price=367)
    body = client.get("/api/search").json()
    assert body["items"][0]["currency"] == "AED"
    assert body["items"][0]["price"] == 367.0
    assert body.get("currency_note") is None


def test_search_with_usd_converts(client, db):
    t = _tenant(db, "cur-usd")
    _svc(db, t, price=367)
    body = client.get("/api/search?currency=USD").json()
    assert body["items"][0]["currency"] == "USD"
    assert body["items"][0]["price"] == 100.0
    assert body["currency_note"] is not None


def test_search_with_eur_converts(client, db):
    t = _tenant(db, "cur-eur")
    _svc(db, t, price=400)
    body = client.get("/api/search?currency=EUR").json()
    assert body["items"][0]["currency"] == "EUR"
    assert body["items"][0]["price"] == 100.0


def test_search_with_invalid_currency_ignored(client, db):
    t = _tenant(db, "cur-bad")
    _svc(db, t, price=500)
    body = client.get("/api/search?currency=XYZ").json()
    # Falls back to AED
    assert body["items"][0]["currency"] == "AED"
    assert body["items"][0]["price"] == 500.0
    assert body.get("currency_note") is None


def test_search_with_aed_explicit(client, db):
    t = _tenant(db, "cur-aed2")
    _svc(db, t, price=500)
    body = client.get("/api/search?currency=AED").json()
    assert body["items"][0]["currency"] == "AED"
    assert body.get("currency_note") is None
