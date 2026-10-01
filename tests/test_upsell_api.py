"""Tests for AI Upsell API (Phase 56, Step 2)."""
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug, typ="hotel"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": 4.5, "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, name, price, typ="room", description=None):
    s = Service(tenant_id=t.id, type=typ, name=name, description=description,
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_upsell_public_no_auth(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ue-api-1")
    base = _svc(db, t, "Standard", 100)
    _svc(db, t, "Breakfast", 30, typ="addon")
    r = client.get(f"/services/{base.id}/upsell")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "suggestions" in body
    assert "rationale" in body
    assert body["status"] in ("ok", "empty")


def test_upsell_service_not_found(client: TestClient) -> None:
    r = client.get("/services/does-not-exist/upsell")
    assert r.status_code == 404


def test_upsell_invalid_language(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ue-api-lang")
    s = _svc(db, t, "Room", 100)
    r = client.get(f"/services/{s.id}/upsell?language=xx")
    assert r.status_code == 422


def test_upsell_returns_suggestions(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ue-api-full")
    base = _svc(db, t, "Standard", 100)
    _svc(db, t, "Deluxe", 200)
    _svc(db, t, "Breakfast Package", 80, typ="addon", description="breakfast add-on")
    r = client.get(f"/services/{base.id}/upsell")
    assert r.status_code == 200, r.text
    body = r.json()
    names = [s["service_name"] for s in body["suggestions"]]
    assert "Deluxe" in names or "Breakfast Package" in names
