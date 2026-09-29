"""Tests for reviews section on tenant home page (Phase 28, Step 5)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db: Session, slug: str) -> Tenant:
    t = Tenant(slug=slug, name="Test Tenant", tier="starter", status="active",
               config={"type": "hotel", "tagline": "Test"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db: Session, tenant: Tenant, email: str) -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U", last_name="X",
        referral_code=email[:10].upper(),
        status="active",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def test_tenant_home_no_reviews_hides_section(client: TestClient, db: Session) -> None:
    t = _tenant(db, "no-reviews-slug")
    r = client.get(f"/{t.slug}/")
    assert r.status_code == 200
    # Section is not rendered when there are no reviews
    assert "Guest reviews" not in r.text


def test_tenant_home_with_review_shows_section(client: TestClient, db: Session) -> None:
    from app.services import review_service

    t = _tenant(db, "has-reviews-slug")
    u = _user(db, t, "guest@x.com")
    review_service.create_review(db, tenant=t, user=u, rating=5, content="Amazing stay, loved it")

    r = client.get(f"/{t.slug}/")
    assert r.status_code == 200
    assert "Guest reviews" in r.text
    assert "px-reviews-grid" in r.text
    assert "Amazing stay, loved it" in r.text


def test_tenant_home_hides_hidden_review(client: TestClient, db: Session) -> None:
    from app.services import review_service

    t = _tenant(db, "hidden-rev-slug")
    u = _user(db, t, "guest2@x.com")
    r1 = review_service.create_review(db, tenant=t, user=u, rating=5, content="Amazing stay, loved it")
    review_service.hide_review(db, t, r1.id)

    r = client.get(f"/{t.slug}/")
    assert r.status_code == 200
    # Section hidden because all reviews are hidden
    assert "Guest reviews" not in r.text


def test_tenant_home_shows_response(client: TestClient, db: Session) -> None:
    from app.services import review_service

    t = _tenant(db, "responded-slug")
    u = _user(db, t, "guest3@x.com")
    rev = review_service.create_review(db, tenant=t, user=u, rating=4, content="Good experience overall")
    review_service.set_response(db, t, rev.id, response_text="Thank you for your visit!", provider="manual")

    r = client.get(f"/{t.slug}/")
    assert r.status_code == 200
    assert "Thank you for your visit!" in r.text
    assert "Response from Test Tenant" in r.text
