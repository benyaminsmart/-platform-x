"""Tests: extended filters in search (Phase 30, Step 9)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug, **cfg):
    base = {"type": "hotel"}
    base.update(cfg)
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config=base)
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, tenant, name="R", price=500, typ="room"):
    s = Service(tenant_id=tenant.id, type=typ, name=name,
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_min_rating_filter(client, db):
    t1 = _tenant(db, "r5", rating=4.8)
    t2 = _tenant(db, "r3", rating=3.2)
    _svc(db, t1, name="A")
    _svc(db, t2, name="B")
    body = client.get("/api/search?min_rating=4.0").json()
    assert body["total"] == 1
    assert body["items"][0]["tenant_slug"] == "r5"


def test_service_type_filter(client, db):
    t = _tenant(db, "typ", type="hotel")
    _svc(db, t, name="Room", typ="room")
    _svc(db, t, name="Table", typ="table")
    _svc(db, t, name="Tour", typ="tour")
    body = client.get("/api/search?service_type=room").json()
    assert body["total"] == 1
    assert body["items"][0]["service_name"] == "Room"


def test_location_filter(client, db):
    t1 = _tenant(db, "loc-dubai", location="Downtown Dubai, UAE")
    t2 = _tenant(db, "loc-abu", location="Abu Dhabi, UAE")
    _svc(db, t1, name="A")
    _svc(db, t2, name="B")
    body = client.get("/api/search?location=dubai").json()
    assert body["total"] == 1
    assert body["items"][0]["tenant_slug"] == "loc-dubai"


def test_location_filter_case_insensitive(client, db):
    t = _tenant(db, "loc-case", location="Downtown Dubai, UAE")
    _svc(db, t, name="A")
    body = client.get("/api/search?location=DUBAI").json()
    assert body["total"] == 1


def test_location_filter_no_match(client, db):
    t = _tenant(db, "loc-nomatch", location="Dubai, UAE")
    _svc(db, t, name="A")
    body = client.get("/api/search?location=paris").json()
    assert body["total"] == 0


def test_combined_filters(client, db):
    t1 = _tenant(db, "comb-ok", rating=4.5, location="Dubai, UAE")
    t2 = _tenant(db, "comb-low-rating", rating=3.0, location="Dubai, UAE")
    t3 = _tenant(db, "comb-wrong-loc", rating=4.8, location="Paris, FR")
    _svc(db, t1, name="Match", price=500, typ="room")
    _svc(db, t2, name="LowRating", price=500, typ="room")
    _svc(db, t3, name="WrongLoc", price=500, typ="room")
    body = client.get("/api/search?min_rating=4.0&location=dubai&service_type=room").json()
    assert body["total"] == 1
    assert body["items"][0]["service_name"] == "Match"


def test_min_rating_validation(client, db):
    r = client.get("/api/search?min_rating=10")
    assert r.status_code == 422
