"""Tests for coordinate seeding (Phase 32, Step 1)."""
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.scripts.seed_coordinates import _coord_for, seed as seed_coords


def _tenant(db, slug, location=None):
    cfg = {"type": "hotel"}
    if location:
        cfg["location"] = location
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config=cfg)
    db.add(t); db.commit(); db.refresh(t)
    return t


def test_coord_for_downtown():
    lat, lng = _coord_for("Downtown Dubai, UAE")
    assert abs(lat - 25.1972) < 0.01
    assert abs(lng - 55.2744) < 0.01


def test_coord_for_marina():
    lat, lng = _coord_for("Marina Walk, Dubai")
    assert abs(lat - 25.0805) < 0.01


def test_coord_for_abu_dhabi():
    lat, lng = _coord_for("Corniche, Abu Dhabi")
    assert abs(lat - 24.4539) < 0.01


def test_coord_for_unknown_falls_back():
    lat, lng = _coord_for("Somewhere Random")
    assert abs(lat - 25.2048) < 0.01
    assert abs(lng - 55.2708) < 0.01


def test_coord_for_none_falls_back():
    lat, lng = _coord_for(None)
    assert abs(lat - 25.2048) < 0.01
