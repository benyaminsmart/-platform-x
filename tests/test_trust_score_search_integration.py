"""Tests for Trust Score in search results + UI badge (Phase 49, Step 3)."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.review import Review
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai", "rating": 4.5})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name=f"Room-{t.slug}",
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _user(db, t, email):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def test_search_payload_includes_trust_score(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ts-search-a")
    _svc(db, t)
    r = client.get("/api/search?category=hotels")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"], "no items returned"
    found = [it for it in body["items"] if it["tenant_slug"] == "ts-search-a"]
    assert found, "tenant not in results"
    assert "trust_score" in found[0]
    assert found[0]["trust_score"] is not None


def test_search_trust_score_higher_for_reviewed_tenant(
    client: TestClient, db: Session
) -> None:
    t1 = _tenant(db, "ts-search-low")
    t2 = _tenant(db, "ts-search-high")
    _svc(db, t1)
    _svc(db, t2)

    # give t2 a pile of 5-star verified+responded reviews
    u = _user(db, t2, "high@x.com")
    for i in range(5):
        r = Review(tenant_id=t2.id, user_id=u.id, rating=5,
                   title="t", content="c", status="published",
                   verified=True, response_text="thanks")
        db.add(r)
    db.commit()

    r = client.get("/api/search?category=hotels")
    body = r.json()
    by_slug = {it["tenant_slug"]: it for it in body["items"]}
    assert "ts-search-low" in by_slug
    assert "ts-search-high" in by_slug
    assert by_slug["ts-search-high"]["trust_score"] > by_slug["ts-search-low"]["trust_score"]


def test_search_page_renders_trust_badge(client: TestClient) -> None:
    r = client.get("/search")
    assert r.status_code == 200
    body = r.text
    assert "sr-trust" in body
    assert "Trust Score" in body
