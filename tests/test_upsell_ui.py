"""Tests for AI Upsell UI on tenant book page (Phase 56, Step 3)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant
from decimal import Decimal


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "rating": 4.5, "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, name, price, typ="room"):
    s = Service(tenant_id=t.id, type=typ, name=name,
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_book_page_renders_upsell_panel(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ue-ui-page")
    _svc(db, t, "Standard", 100)
    r = client.get(f"/{t.slug}/book")
    assert r.status_code == 200, r.text
    body = r.text
    assert 'id="upsell-panel"' in body
    assert 'id="upsell-rationale"' in body
    assert 'id="upsell-list"' in body
    assert 'id="upsell-close"' in body
    assert "Recommended add-ons" in body


def test_book_page_calls_upsell_endpoint(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ue-ui-api")
    _svc(db, t, "Standard", 100)
    r = client.get(f"/{t.slug}/book")
    body = r.text
    assert "/upsell" in body
    assert "/services/" in body
