"""Tests for attractions API (Phase 41, Step 2)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.attraction import Attraction


def _seed(db: Session) -> None:
    db.add(Attraction(name="A1", category="landmark", lat=25.20, lng=55.27, city="Dubai"))
    db.add(Attraction(name="A2", category="park", lat=25.21, lng=55.28, city="Dubai"))
    db.add(Attraction(name="Far", category="park", lat=24.45, lng=54.38, city="Abu Dhabi"))
    db.commit()


def test_list_all(client: TestClient, db: Session) -> None:
    _seed(db)
    r = client.get("/api/attractions")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_nearby_returns_within_radius(client: TestClient, db: Session) -> None:
    _seed(db)
    r = client.get("/api/attractions/nearby?lat=25.2048&lng=55.2708&radius_km=5")
    assert r.status_code == 200
    rows = r.json()
    names = [x["name"] for x in rows]
    assert "A1" in names
    assert "A2" in names
    assert "Far" not in names


def test_nearby_sorted_by_distance(client: TestClient, db: Session) -> None:
    _seed(db)
    r = client.get("/api/attractions/nearby?lat=25.20&lng=55.27&radius_km=50")
    rows = r.json()
    dists = [x["distance_km"] for x in rows]
    assert dists == sorted(dists)


def test_nearby_validates_lat(client: TestClient, db: Session) -> None:
    r = client.get("/api/attractions/nearby?lat=999&lng=55")
    assert r.status_code == 422


def test_nearby_empty(client: TestClient, db: Session) -> None:
    r = client.get("/api/attractions/nearby?lat=0&lng=0&radius_km=1")
    assert r.status_code == 200
    assert r.json() == []
