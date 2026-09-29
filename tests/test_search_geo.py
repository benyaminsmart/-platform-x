"""Tests: geographic filter in search (Phase 32, Step 2)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug, lat=25.2048, lng=55.2708, location="Dubai, UAE"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": location,
                       "coordinates": {"lat": lat, "lng": lng}})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, tenant, name="R"):
    s = Service(tenant_id=tenant.id, type="room", name=name,
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_search_no_geo_returns_all(client, db):
    t1 = _tenant(db, "geo-a", lat=25.20, lng=55.27)
    t2 = _tenant(db, "geo-b", lat=24.45, lng=54.38)  # Abu Dhabi ~130km away
    _svc(db, t1, "A"); _svc(db, t2, "B")
    body = client.get("/api/search").json()
    assert body["total"] == 2
    # No geo, no distance
    assert all(i["distance_km"] is None for i in body["items"])


def test_search_within_radius(client, db):
    t1 = _tenant(db, "geo-close", lat=25.20, lng=55.27)
    t2 = _tenant(db, "geo-far", lat=24.45, lng=54.38)
    _svc(db, t1, "Close"); _svc(db, t2, "Far")
    # Search from Dubai center with 20km radius
    body = client.get("/api/search?lat=25.2048&lng=55.2708&radius_km=20").json()
    assert body["total"] == 1
    assert body["items"][0]["service_name"] == "Close"
    assert body["items"][0]["distance_km"] is not None
    assert body["items"][0]["distance_km"] < 5


def test_search_far_radius(client, db):
    t1 = _tenant(db, "geo-all-a", lat=25.20, lng=55.27)
    t2 = _tenant(db, "geo-all-b", lat=24.45, lng=54.38)
    _svc(db, t1, "A"); _svc(db, t2, "B")
    # 200km radius includes both
    body = client.get("/api/search?lat=25.2048&lng=55.2708&radius_km=200").json()
    assert body["total"] == 2


def test_search_excludes_tenants_without_coords(client, db):
    t1 = _tenant(db, "geo-has", lat=25.20, lng=55.27)
    t2 = Tenant(slug="geo-no-coord", name="X", tier="starter", status="active",
                config={"type": "hotel", "location": "Dubai"})
    db.add(t2); db.commit(); db.refresh(t2)
    _svc(db, t1, "Has"); _svc(db, t2, "None")
    body = client.get("/api/search?lat=25.2048&lng=55.2708&radius_km=20").json()
    assert body["total"] == 1
    assert body["items"][0]["service_name"] == "Has"


def test_search_coordinates_in_response(client, db):
    t = _tenant(db, "geo-coords", lat=25.20, lng=55.27)
    _svc(db, t, "A")
    body = client.get("/api/search").json()
    assert body["items"][0]["coordinates"]["lat"] == 25.20


def test_lat_validation(client, db):
    r = client.get("/api/search?lat=999&lng=55")
    assert r.status_code == 422
