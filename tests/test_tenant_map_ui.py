"""Tests: map section on tenant page (Phase 32, Step 4)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.tenant import Tenant


def _tenant(db, slug, lat=25.20, lng=55.27):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai, UAE",
                       "coordinates": {"lat": lat, "lng": lng}})
    db.add(t); db.commit(); db.refresh(t)
    return t


def test_tenant_page_has_map_section(client: TestClient, db: Session) -> None:
    t = _tenant(db, "tm-ui")
    r = client.get(f"/{t.slug}/")
    assert r.status_code == 200
    html = r.text
    assert 'id="tm-map"' in html
    assert 'id="tm-find-near"' in html
    assert 'id="tm-open-maps"' in html
    assert "leaflet" in html.lower()
    assert "25.2" in html  # lat rendered


def test_tenant_page_map_uses_coordinates(client: TestClient, db: Session) -> None:
    t = _tenant(db, "tm-coord", lat=24.45, lng=54.38)
    r = client.get(f"/{t.slug}/")
    html = r.text
    assert "24.45" in html
    assert "54.38" in html


def test_tenant_page_has_find_nearby_button(client: TestClient, db: Session) -> None:
    t = _tenant(db, "tm-near")
    r = client.get(f"/{t.slug}/")
    assert "/search?" in r.text
    assert "radius_km" in r.text
