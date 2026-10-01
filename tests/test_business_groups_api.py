"""Tests for Business Group API (Phase 58, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug, typ="hotel", rating=4.5):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": rating, "location": "Dubai",
                       "currency": "AED"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _owner(db, tenant, email):
    # referral_code must be globally unique — mix tenant slug
    rc = ("OWN" + email.split("@")[0].upper() + "-" + tenant.slug.upper())[:30]
    u = User(tenant_id=tenant.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="O", last_name="X", business_role="owner",
             referral_code=rc, status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name=f"R-{t.slug}",
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _login(client, slug, email):
    r = client.post("/auth/login",
                    json={"email": email, "password": "Pass1234"},
                    headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_requires_auth(client: TestClient) -> None:
    r = client.get("/business/api/groups")
    assert r.status_code == 401


def test_create_list_group(client: TestClient, db: Session) -> None:
    t = _tenant(db, "bg-api-1")
    u = _owner(db, t, "owner1@x.com")
    token = _login(client, t.slug, u.email)
    h = {"Authorization": f"Bearer {token}"}

    r = client.post("/business/api/groups", json={"name": "My Chain"}, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["slug"] == "my-chain"

    r = client.get("/business/api/groups", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_create_group_empty_name(client: TestClient, db: Session) -> None:
    t = _tenant(db, "bg-api-empty")
    u = _owner(db, t, "empty1@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/business/api/groups", json={"name": ""},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_attach_and_detail(client: TestClient, db: Session) -> None:
    t1 = _tenant(db, "bg-api-att-1")
    t2 = _tenant(db, "bg-api-att-2")
    u1 = _owner(db, t1, "chain@x.com")
    _owner(db, t2, "chain@x.com")
    _svc(db, t1)
    _svc(db, t2)

    token = _login(client, t1.slug, u1.email)
    h = {"Authorization": f"Bearer {token}"}

    r = client.post("/business/api/groups", json={"name": "Chain"}, headers=h)
    gid = r.json()["id"]

    r = client.post(f"/business/api/groups/{gid}/attach",
                    json={"tenant_slug": t2.slug}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["members_count"] == 1

    r = client.get(f"/business/api/groups/{gid}", headers=h)
    assert r.status_code == 200
    detail = r.json()
    assert detail["metrics"]["members_count"] == 1
    assert detail["metrics"]["services_count"] == 1


def test_detach_member(client: TestClient, db: Session) -> None:
    t1 = _tenant(db, "bg-api-det-1")
    t2 = _tenant(db, "bg-api-det-2")
    u = _owner(db, t1, "det1@x.com")
    _owner(db, t2, "det1@x.com")
    token = _login(client, t1.slug, u.email)
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/business/api/groups", json={"name": "G"}, headers=h)
    gid = r.json()["id"]
    client.post(f"/business/api/groups/{gid}/attach",
                json={"tenant_slug": t2.slug}, headers=h)
    r = client.delete(f"/business/api/groups/{gid}/members/{t2.slug}", headers=h)
    assert r.status_code == 200
    assert r.json()["detached"] is True


def test_delete_group(client: TestClient, db: Session) -> None:
    t = _tenant(db, "bg-api-del")
    u = _owner(db, t, "del1@x.com")
    token = _login(client, t.slug, u.email)
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/business/api/groups", json={"name": "ToDelete"}, headers=h)
    gid = r.json()["id"]
    r = client.delete(f"/business/api/groups/{gid}", headers=h)
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    r = client.get(f"/business/api/groups/{gid}", headers=h)
    assert r.status_code == 404


def test_cross_owner_isolation(client: TestClient, db: Session) -> None:
    t1 = _tenant(db, "bg-api-iso-1")
    t2 = _tenant(db, "bg-api-iso-2")
    u1 = _owner(db, t1, "iso1@x.com")
    u2 = _owner(db, t2, "iso2@x.com")
    tok1 = _login(client, t1.slug, u1.email)
    tok2 = _login(client, t2.slug, u2.email)
    r = client.post("/business/api/groups", json={"name": "U1Group"},
                    headers={"Authorization": f"Bearer {tok1}"})
    gid = r.json()["id"]
    r = client.get(f"/business/api/groups/{gid}",
                   headers={"Authorization": f"Bearer {tok2}"})
    assert r.status_code == 404
