"""Tests for AI location recommend API (Phase 45, Step 2)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.attraction import Attraction
from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug, lat=25.20, lng=55.27):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "rating": 4.5, "location": "Dubai",
                       "coordinates": {"lat": lat, "lng": lng}})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name="R",
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _attraction(db, name):
    a = Attraction(name=name, category="landmark", lat=25.20, lng=55.27, city="Dubai")
    db.add(a); db.commit()
    return a


def test_location_recommend_empty(client: TestClient) -> None:
    r = client.post("/ai/location/recommend",
                    json={"lat": 0.0, "lng": 0.0, "radius_km": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["attractions"] == []
    assert body["services"] == []
    assert body["advice"]


def test_location_recommend_with_data(client: TestClient, db: Session) -> None:
    t = _tenant(db, "loc-api")
    _svc(db, t)
    _attraction(db, "Test Landmark")
    r = client.post("/ai/location/recommend",
                    json={"lat": 25.20, "lng": 55.27, "radius_km": 5})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["services"]) >= 1
    assert len(body["attractions"]) >= 1


def test_location_recommend_invalid_lang(client: TestClient) -> None:
    r = client.post("/ai/location/recommend",
                    json={"lat": 25.2, "lng": 55.27, "language": "xx"})
    assert r.status_code == 422


def test_location_recommend_invalid_lat(client: TestClient) -> None:
    r = client.post("/ai/location/recommend",
                    json={"lat": 999, "lng": 55.27})
    assert r.status_code == 422
