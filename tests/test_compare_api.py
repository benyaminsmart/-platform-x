"""Tests for compare API (Phase 33, Step 5)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug, rating=4.5):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "rating": rating, "location": "Dubai, UAE"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, name="R", price=500):
    s = Service(tenant_id=t.id, type="room", name=name,
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={"view": "sea"}, image_urls=["https://x/a.jpg"],
                status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_compare_two(client, db):
    t1 = _tenant(db, "cmp-a")
    t2 = _tenant(db, "cmp-b")
    s1 = _svc(db, t1, "A", 500)
    s2 = _svc(db, t2, "B", 800)
    r = client.get(f"/api/compare?ids={s1.id},{s2.id}")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["service_name"] == "A"


def test_compare_order_preserved(client, db):
    t = _tenant(db, "cmp-ord")
    s1 = _svc(db, t, "A")
    s2 = _svc(db, t, "B")
    body = client.get(f"/api/compare?ids={s2.id},{s1.id}").json()
    assert body["items"][0]["service_name"] == "B"


def test_compare_needs_two(client, db):
    t = _tenant(db, "cmp-min")
    s = _svc(db, t, "A")
    r = client.get(f"/api/compare?ids={s.id}")
    assert r.status_code == 400


def test_compare_max_4(client, db):
    t = _tenant(db, "cmp-max")
    ids = [_svc(db, t, f"S{i}").id for i in range(6)]
    body = client.get("/api/compare?ids=" + ",".join(ids)).json()
    assert len(body["items"]) == 4


def test_compare_skips_unknown(client, db):
    t = _tenant(db, "cmp-unk")
    s = _svc(db, t, "A")
    body = client.get(f"/api/compare?ids={s.id},nonexistent").json()
    assert len(body["items"]) == 1
