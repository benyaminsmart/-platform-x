"""Tests for review photos on tenant page (Phase 39, Step 2)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.services import review_service


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def test_tenant_page_has_review_photos_placeholder(client: TestClient, db: Session) -> None:
    t = _tenant(db, "rvp-ui")
    u = _user(db, t)
    review_service.create_review(db, tenant=t, user=u, rating=5, content="Amazing stay, loved it")
    r = client.get(f"/{t.slug}/")
    assert r.status_code == 200
    html = r.text
    assert "px-review-photos" in html
    assert "px-review-photo-lightbox" in html
    assert "/photos" in html
