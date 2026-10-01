"""Tests for Local Experiences API (Phase 65, Step 2)."""
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.local_event import LocalEvent


def _event(db, name, lat, lng, city, *, days_from_now=2, duration_days=30,
           category="festival"):
    start = datetime.now(timezone.utc) + timedelta(days=days_from_now)
    e = LocalEvent(name=name, category=category, city=city, venue=f"V-{city}",
                   lat=lat, lng=lng, start_at=start,
                   end_at=start + timedelta(days=duration_days),
                   description="desc")
    db.add(e); db.commit(); db.refresh(e)
    return e


def test_list_events_public_no_auth(client: TestClient, db: Session) -> None:
    _event(db, "E1", 25.20, 55.27, "Dubai")
    r = client.get("/api/local-events")
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1


def test_list_events_filter_city(client: TestClient, db: Session) -> None:
    _event(db, "A", 25.20, 55.27, "Dubai")
    _event(db, "B", 24.45, 54.38, "Abu Dhabi")
    r = client.get("/api/local-events?city=Dubai")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["city"] == "Dubai"


def test_nearby_returns_distance(client: TestClient, db: Session) -> None:
    _event(db, "Near", 25.20, 55.27, "Dubai")
    r = client.get("/api/local-events/nearby?lat=25.20&lng=55.27&radius_km=5")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert "distance_km" in body[0]


def test_nearby_empty_when_no_events(client: TestClient) -> None:
    r = client.get("/api/local-events/nearby?lat=0&lng=0&radius_km=1")
    assert r.status_code == 200
    assert r.json() == []


def test_nearby_invalid_lat(client: TestClient) -> None:
    r = client.get("/api/local-events/nearby?lat=999&lng=0")
    assert r.status_code == 422


def test_recommend_ok(client: TestClient, db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_ADVICE", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    _event(db, "Rec E", 25.20, 55.27, "Dubai")
    r = client.post("/api/local-events/recommend",
                    json={"lat": 25.20, "lng": 55.27, "radius_km": 5})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "ai"
    assert body["advice"] == "AI_ADVICE"
    assert len(body["events"]) == 1


def test_recommend_empty_fallback(client: TestClient) -> None:
    r = client.post("/api/local-events/recommend",
                    json={"lat": 0, "lng": 0, "radius_km": 1})
    assert r.status_code == 200
    assert r.json()["provider"] == "fallback"


def test_recommend_invalid_lang(client: TestClient) -> None:
    r = client.post("/api/local-events/recommend",
                    json={"lat": 25.2, "lng": 55.27, "language": "xx"})
    assert r.status_code == 422
