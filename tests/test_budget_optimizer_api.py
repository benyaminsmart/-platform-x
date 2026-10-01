"""Tests for Budget Optimizer API (Phase 50, Step 2)."""
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug, typ="hotel", location="Dubai", rating=4.5):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": rating, "location": location})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, price=500, typ="room"):
    s = Service(tenant_id=t.id, type=typ, name=f"{typ.capitalize()}-{t.slug}",
                price=Decimal(str(price)), currency="AED", capacity=4,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_optimize_public_no_auth(client: TestClient) -> None:
    r = client.post("/api/budget-optimize", json={"budget": 2000})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "package" in body
    assert "advice" in body


def test_optimize_with_services(client: TestClient, db: Session) -> None:
    th = _tenant(db, "bo-api-h", typ="hotel", rating=4.8)
    tr = _tenant(db, "bo-api-r", typ="restaurant", rating=4.6)
    _svc(db, th, price=400, typ="room")
    _svc(db, tr, price=80, typ="table")

    r = client.post("/api/budget-optimize",
                    json={"budget": 5000, "city": "Dubai", "days": 3, "guests": 2})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["package"]
    cats = {p["category"] for p in body["package"]}
    assert "hotels" in cats


def test_optimize_invalid_language(client: TestClient) -> None:
    r = client.post("/api/budget-optimize", json={"budget": 2000, "language": "xx"})
    assert r.status_code == 422


def test_optimize_invalid_budget(client: TestClient) -> None:
    r = client.post("/api/budget-optimize", json={"budget": 0})
    assert r.status_code == 422


def test_optimize_invalid_days(client: TestClient) -> None:
    r = client.post("/api/budget-optimize", json={"budget": 2000, "days": 0})
    assert r.status_code == 422


def test_optimize_invalid_guests(client: TestClient) -> None:
    r = client.post("/api/budget-optimize", json={"budget": 2000, "guests": 100})
    assert r.status_code == 422
