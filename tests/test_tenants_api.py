"""Tests for public tenant endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.tenant import Tenant


def test_list_tenants_empty(client: TestClient) -> None:
    resp = client.get("/tenants")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_tenants_returns_active_only(
    client: TestClient, db: Session, sample_tenant: Tenant
) -> None:
    inactive = Tenant(
        slug="inactive", name="Inactive Co", tier="starter", status="suspended", config={}
    )
    db.add(inactive)
    db.commit()

    resp = client.get("/tenants")
    assert resp.status_code == 200
    slugs = [t["slug"] for t in resp.json()]
    assert "demo" in slugs
    assert "inactive" not in slugs


def test_tenants_sorted_by_name(
    client: TestClient, db: Session, sample_tenant: Tenant
) -> None:
    db.add(Tenant(slug="a-corp", name="A Corp", tier="starter", status="active", config={}))
    db.add(Tenant(slug="z-corp", name="Z Corp", tier="starter", status="active", config={}))
    db.commit()

    resp = client.get("/tenants")
    names = [t["name"] for t in resp.json()]
    assert names == sorted(names)


def test_current_tenant_returns_config(
    client: TestClient, sample_tenant: Tenant
) -> None:
    sample_tenant.config = {"type": "hotel", "branding": {"primary_color": "#000"}}
    # re-fetch through API; note sample_tenant is attached to the test session
    # which is the same session the endpoint uses via dependency override.
    resp = client.get(
        "/tenants/current", headers={"X-Tenant-Slug": sample_tenant.slug}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "demo"
    assert data["name"] == "Demo Business"
    assert data["config"]["type"] == "hotel"


def test_current_tenant_unknown_404(client: TestClient) -> None:
    resp = client.get("/tenants/current", headers={"X-Tenant-Slug": "ghost"})
    assert resp.status_code == 404
