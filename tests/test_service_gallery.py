"""Tests for service gallery API (Phase 30, Step 10)."""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.service import Service
from app.models.tenant import Tenant


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, tenant, imgs=None, attrs=None):
    if imgs is None:
        imgs = ["https://img1.example.com/a.jpg", "https://img2.example.com/b.jpg"]
    if attrs is None:
        attrs = {"bed": "king", "view": "sea"}
    s = Service(tenant_id=tenant.id, type="room", name="Deluxe Suite",
                price=Decimal("800"), currency="AED", capacity=2,
                attributes=attrs,
                image_urls=imgs,
                status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_gallery_not_found(client, db):
    t = _tenant(db, "gal-nf")
    r = client.get("/services/nope/gallery", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 404


def test_gallery_returns_images(client, db):
    t = _tenant(db, "gal-ok")
    s = _svc(db, t)
    r = client.get(f"/services/{s.id}/gallery", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 200
    body = r.json()
    assert body["service_name"] == "Deluxe Suite"
    assert len(body["images"]) == 2
    assert body["attributes"]["bed"] == "king"
    assert body["capacity"] == 2
    assert body["price"] == "800.00"


def test_gallery_empty_ok(client, db):
    t = _tenant(db, "gal-empty")
    s = _svc(db, t, imgs=[], attrs={})
    r = client.get(f"/services/{s.id}/gallery", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 200
    assert r.json()["images"] == []
    assert r.json()["attributes"] == {}


def test_gallery_cross_tenant_blocked(client, db):
    t1 = _tenant(db, "gal-a")
    t2 = _tenant(db, "gal-b")
    s2 = _svc(db, t2)
    r = client.get(f"/services/{s2.id}/gallery", headers={"X-Tenant-Slug": t1.slug})
    assert r.status_code == 404
