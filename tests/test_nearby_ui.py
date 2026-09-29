"""Tests for nearby attractions section on tenant page (Phase 41, Step 3)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.tenant import Tenant


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "coordinates": {"lat": 25.20, "lng": 55.27}})
    db.add(t); db.commit(); db.refresh(t)
    return t


def test_tenant_page_has_nearby_section(client: TestClient, db: Session) -> None:
    t = _tenant(db, "nb-ui")
    r = client.get(f"/{t.slug}/")
    assert r.status_code == 200
    html = r.text
    assert "Nearby attractions" in html
    assert 'id="tn-body"' in html
    assert "/api/attractions/nearby" in html
    assert "distance_km" in html
