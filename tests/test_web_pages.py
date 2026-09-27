"""Tests for HTML pages (Jinja2)."""

from fastapi.testclient import TestClient

from app.models.service import Service
from app.models.tenant import Tenant


def test_home_page(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Platform-X" in resp.text
    assert "One platform" in resp.text


def test_businesses_page_lists_tenants(
    client: TestClient, sample_tenant: Tenant
) -> None:
    resp = client.get("/businesses")
    assert resp.status_code == 200
    assert "Demo Business" in resp.text


def test_businesses_page_empty(client: TestClient) -> None:
    resp = client.get("/businesses")
    assert resp.status_code == 200
    assert "No businesses yet" in resp.text


def test_about_page(client: TestClient) -> None:
    resp = client.get("/about")
    assert resp.status_code == 200
    assert "One platform for every kind" in resp.text


def test_contact_page(client: TestClient) -> None:
    resp = client.get("/contact")
    assert resp.status_code == 200
    assert "Get in touch" in resp.text


def test_tenant_home_loads(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    db.add(Service(
        tenant_id=sample_tenant.id, type="room", name="Test Suite", price=500
    ))
    db.commit()

    resp = client.get(f"/{sample_tenant.slug}/")
    assert resp.status_code == 200
    assert "Demo Business" in resp.text
    assert "Test Suite" in resp.text


def test_tenant_home_unknown_slug_404(client: TestClient) -> None:
    resp = client.get("/does-not-exist/")
    assert resp.status_code == 404


def test_tenant_home_reserved_slug_404(client: TestClient) -> None:
    """A reserved slug like /businesses/ should NOT be treated as a tenant."""
    resp = client.get("/businesses/", follow_redirects=False)
    assert resp.status_code == 307


def test_tenant_home_only_active_services(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    db.add(Service(
        tenant_id=sample_tenant.id, type="room", name="Active", price=100,
        status="active",
    ))
    db.add(Service(
        tenant_id=sample_tenant.id, type="room", name="Inactive", price=100,
        status="inactive",
    ))
    db.commit()

    resp = client.get(f"/{sample_tenant.slug}/")
    assert resp.status_code == 200
    assert "Active" in resp.text
    assert "Inactive" not in resp.text


def test_tenant_home_suspended_tenant_404(
    client: TestClient, db
) -> None:
    t = Tenant(slug="suspended", name="Suspended Co", tier="starter",
               status="suspended", config={})
    db.add(t)
    db.commit()
    resp = client.get("/suspended/")
    assert resp.status_code == 404
