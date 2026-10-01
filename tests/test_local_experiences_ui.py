"""Tests for Local Experiences UI on tenant page (Phase 65, Step 3)."""
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "rating": 4.5, "location": "Dubai",
                       "coordinates": {"lat": 25.20, "lng": 55.27}})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name="Room",
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_tenant_home_has_events_section(client: TestClient, db: Session) -> None:
    t = _tenant(db, "lx-ui-1")
    _svc(db, t)
    r = client.get(f"/{t.slug}/")
    assert r.status_code == 200
    body = r.text
    assert 'id="te-body"' in body
    assert "What's happening nearby" in body


def test_tenant_home_calls_local_events_api(client: TestClient, db: Session) -> None:
    t = _tenant(db, "lx-ui-2")
    _svc(db, t)
    r = client.get(f"/{t.slug}/")
    body = r.text
    assert "/api/local-events/nearby" in body
    assert "px-te-card" in body
