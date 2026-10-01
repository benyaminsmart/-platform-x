"""Tests for Family & Kids Mode filter (Phase 55, Step 1)."""
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant
from app.services import search_service


def _tenant(db, slug, amenities=None, typ="hotel", family=None):
    cfg = {"type": typ, "rating": 4.5, "location": "Dubai",
           "amenities": amenities or []}
    if family is not None:
        cfg["family_friendly"] = family
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config=cfg)
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, name="Room", description=None, attributes=None):
    s = Service(tenant_id=t.id, type="room", name=name,
                description=description,
                price=Decimal("500"), currency="AED", capacity=2,
                attributes=attributes or {}, image_urls=[],
                status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_family_filter_excludes_non_family(db: Session) -> None:
    t_plain = _tenant(db, "fam-plain")
    _svc(db, t_plain, name="Standard Room")
    out = search_service.search_services(db, family_friendly=True)
    slugs = [it["tenant_slug"] for it in out["items"]]
    assert "fam-plain" not in slugs


def test_family_filter_includes_tenant_with_kids_amenity(db: Session) -> None:
    t = _tenant(db, "fam-kids-amenity", amenities=["Kids club", "Pool"])
    _svc(db, t, name="Room")
    out = search_service.search_services(db, family_friendly=True)
    slugs = [it["tenant_slug"] for it in out["items"]]
    assert "fam-kids-amenity" in slugs


def test_family_filter_includes_service_with_family_attr(db: Session) -> None:
    t = _tenant(db, "fam-attr")
    _svc(db, t, name="Room", attributes={"family_friendly": True})
    out = search_service.search_services(db, family_friendly=True)
    slugs = [it["tenant_slug"] for it in out["items"]]
    assert "fam-attr" in slugs


def test_family_filter_includes_service_by_name_keyword(db: Session) -> None:
    t = _tenant(db, "fam-name")
    _svc(db, t, name="Family Suite")
    out = search_service.search_services(db, family_friendly=True)
    slugs = [it["tenant_slug"] for it in out["items"]]
    assert "fam-name" in slugs


def test_family_filter_disabled_shows_all(db: Session) -> None:
    t = _tenant(db, "fam-all")
    _svc(db, t, name="Standard Room")
    out = search_service.search_services(db)  # no filter
    slugs = [it["tenant_slug"] for it in out["items"]]
    assert "fam-all" in slugs


def test_family_flag_present_in_payload(db: Session) -> None:
    t1 = _tenant(db, "fam-pay-yes", amenities=["Kids club"])
    t2 = _tenant(db, "fam-pay-no")
    _svc(db, t1, name="Room A")
    _svc(db, t2, name="Room B")
    out = search_service.search_services(db)
    by_slug = {it["tenant_slug"]: it for it in out["items"]}
    assert by_slug["fam-pay-yes"]["family_friendly"] is True
    assert by_slug["fam-pay-no"]["family_friendly"] is False


def test_api_family_query_param(client: TestClient, db: Session) -> None:
    t = _tenant(db, "fam-api", amenities=["Kids club"])
    _svc(db, t, name="Room")
    r = client.get("/api/search?family_friendly=true")
    assert r.status_code == 200, r.text
    body = r.json()
    for it in body["items"]:
        assert it["family_friendly"] is True
