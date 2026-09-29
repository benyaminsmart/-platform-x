"""Tests: service gallery section on tenant page (Phase 30, Step 10b)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.tenant import Tenant


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def test_tenant_page_has_gallery_section(client: TestClient, db: Session) -> None:
    t = _tenant(db, "gal-ui")
    r = client.get(f"/{t.slug}/")
    assert r.status_code == 200
    html = r.text
    assert "Rooms &amp; services" in html or "Rooms & services" in html
    assert 'id="tg-body"' in html
    assert "/services/" in html
    assert "/gallery" in html
    assert "px-tg-lightbox" in html
