"""Tests for Attraction model + seed (Phase 41, Step 1)."""
from sqlalchemy.orm import Session
from app.models.attraction import Attraction


def test_attraction_create(db: Session) -> None:
    a = Attraction(name="Test Landmark", category="landmark", lat=25.0, lng=55.0)
    db.add(a); db.commit(); db.refresh(a)
    assert a.id
    assert a.category == "landmark"


def test_attraction_defaults(db: Session) -> None:
    a = Attraction(name="X", category="park", lat=1.0, lng=2.0)
    db.add(a); db.commit(); db.refresh(a)
    assert a.description is None
    assert a.city is None
    assert a.cover_image is None
    assert a.extra == {}
