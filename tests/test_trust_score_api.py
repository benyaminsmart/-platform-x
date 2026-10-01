"""Tests for Trust Score API (Phase 49, Step 2)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.review import Review
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _review(db, t, u, rating=5, verified=True, responded=True):
    r = Review(tenant_id=t.id, user_id=u.id, rating=rating,
               title="t", content="c", status="published", verified=verified,
               response_text=("r" if responded else None))
    db.add(r); db.commit(); db.refresh(r)
    return r


def test_get_trust_score_not_found(client: TestClient) -> None:
    r = client.get("/api/trust-score/does-not-exist")
    assert r.status_code == 404


def test_get_trust_score_ok(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ts-api-1")
    u = _user(db, t, "u@x.com")
    _review(db, t, u, rating=5, verified=True, responded=True)
    r = client.get("/api/trust-score/ts-api-1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_slug"] == "ts-api-1"
    assert body["score"] > 0
    assert "rating" in body["components"]
    assert "rating" in body["weights"]


def test_bulk_endpoint(client: TestClient, db: Session) -> None:
    t1 = _tenant(db, "ts-api-b1")
    t2 = _tenant(db, "ts-api-b2")
    r = client.post("/api/trust-score/bulk",
                    json={"tenant_ids": [t1.id, t2.id]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 2
    ids = {it["tenant_id"] for it in body["items"]}
    assert t1.id in ids and t2.id in ids


def test_bulk_empty_rejected(client: TestClient) -> None:
    r = client.post("/api/trust-score/bulk", json={"tenant_ids": []})
    assert r.status_code == 422


def test_bulk_too_many_rejected(client: TestClient) -> None:
    r = client.post("/api/trust-score/bulk",
                    json={"tenant_ids": ["x"] * 51})
    assert r.status_code == 422
