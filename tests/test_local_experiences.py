"""Tests for Local Experiences service (Phase 65, Step 1)."""
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.local_event import LocalEvent
from app.services import local_experiences as lx


def _event(db, name, lat, lng, city, *, days_from_now=2, category="festival",
           duration_days=30):
    start = datetime.now(timezone.utc) + timedelta(days=days_from_now)
    e = LocalEvent(name=name, category=category, city=city, venue=f"Venue-{city}",
                   lat=lat, lng=lng,
                   start_at=start,
                   end_at=start + timedelta(days=duration_days),
                   description="desc")
    db.add(e); db.commit(); db.refresh(e)
    return e


def test_invalid_language(db):
    with pytest.raises(ValueError):
        lx.recommend(db, lat=25.20, lng=55.27, language="xx")


def test_empty_recommend(db):
    out = lx.recommend(db, lat=0.0, lng=0.0, radius_km=1)
    assert out["events"] == []
    assert out["provider"] == "fallback"
    assert "No local events" in out["advice"]


def test_nearby_returns_events(db):
    _event(db, "Test Fest Dubai", 25.20, 55.27, "Dubai", days_from_now=2)
    out = lx.nearby(db, lat=25.20, lng=55.27, radius_km=5)
    assert len(out) == 1
    assert out[0]["name"] == "Test Fest Dubai"
    assert "distance_km" in out[0]


def test_nearby_excludes_far(db):
    _event(db, "Far Event", 40.0, 40.0, "Nowhere", days_from_now=2)
    out = lx.nearby(db, lat=25.20, lng=55.27, radius_km=5)
    assert out == []


def test_nearby_date_filter_includes(db):
    on_date = date.today() + timedelta(days=3)
    _event(db, "Current Event", 25.20, 55.27, "Dubai",
           days_from_now=2, duration_days=30)
    out = lx.nearby(db, lat=25.20, lng=55.27, radius_km=5, on_date=on_date)
    assert len(out) == 1


def test_nearby_date_filter_excludes_expired(db):
    _event(db, "Old Event", 25.20, 55.27, "Dubai",
           days_from_now=-60, duration_days=2)  # already over
    on_date = date.today() + timedelta(days=2)
    out = lx.nearby(db, lat=25.20, lng=55.27, radius_km=5, on_date=on_date)
    assert out == []


def test_list_events_by_city(db):
    _event(db, "A Dubai", 25.20, 55.27, "Dubai")
    _event(db, "B Abu Dhabi", 24.45, 54.38, "Abu Dhabi")
    out = lx.list_events(db, city="Dubai")
    assert len(out) == 1
    assert out[0]["city"] == "Dubai"


def test_recommend_with_ai(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_ADVICE", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    _event(db, "Event A", 25.20, 55.27, "Dubai")
    out = lx.recommend(db, lat=25.20, lng=55.27, radius_km=5)
    assert out["provider"] == "ai"
    assert out["advice"] == "AI_ADVICE"
    assert len(out["events"]) == 1


def test_recommend_fallback(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    _event(db, "Event B", 25.20, 55.27, "Dubai")
    out = lx.recommend(db, lat=25.20, lng=55.27, radius_km=5)
    assert out["provider"] == "fallback"
    assert "Event B" in out["advice"]
