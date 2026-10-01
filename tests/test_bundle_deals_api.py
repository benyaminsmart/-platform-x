"""Tests for Bundle Deals API (Phase 51, Step 2)."""
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
    s = Service(tenant_id=t.id, type=typ, name=f"{typ}-{t.slug}",
                price=Decimal(str(price)), currency="AED", capacity=4,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_bundle_public_no_auth(client: TestClient) -> None:
    r = client.post("/api/bundle-deals", json={"city": "Atlantis"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert "advice" in body


def test_bundle_with_services(client: TestClient, db: Session) -> None:
    th = _tenant(db, "bd-api-h", typ="hotel", rating=4.8)
    tr = _tenant(db, "bd-api-r", typ="restaurant", rating=4.6)
    _svc(db, th, price=400, typ="room")
    _svc(db, tr, price=80, typ="table")

    r = client.post("/api/bundle-deals",
                    json={"city": "Dubai", "days": 3, "guests": 2})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"]
    assert body["discount_percent"] >= 0
    assert body["total"] <= body["subtotal"]


def test_bundle_invalid_language(client: TestClient) -> None:
    r = client.post("/api/bundle-deals", json={"language": "xx"})
    assert r.status_code == 422


def test_bundle_invalid_days(client: TestClient) -> None:
    r = client.post("/api/bundle-deals", json={"days": 0})
    assert r.status_code == 422


def test_bundle_invalid_guests(client: TestClient) -> None:
    r = client.post("/api/bundle-deals", json={"guests": 100})
    assert r.status_code == 422
