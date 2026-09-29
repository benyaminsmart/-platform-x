"""Tests for availability section on tenant page (Phase 30, Step 4b)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.tenant import Tenant


def _tenant(db: Session, slug: str) -> Tenant:
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def test_availability_section_renders(client: TestClient, db: Session) -> None:
    t = _tenant(db, "avt-home")
    r = client.get(f"/{t.slug}/")
    assert r.status_code == 200
    html = r.text
    assert "Availability — next 14 days" in html
    assert 'id="av-body"' in html
    assert "/api/availability/" in html


def test_availability_section_links_to_search(client: TestClient, db: Session) -> None:
    t = _tenant(db, "avt-links")
    r = client.get(f"/{t.slug}/")
    html = r.text
    # JS embeds search link template
    assert "/search?tenant=" in html
    assert "check_in=" in html
