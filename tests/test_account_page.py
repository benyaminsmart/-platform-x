"""Tests for account HTML page."""

from fastapi.testclient import TestClient

from app.models.tenant import Tenant


def test_account_page_loads(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.get(f"/{sample_tenant.slug}/account")
    assert resp.status_code == 200
    assert "My Account" in resp.text
    assert 'id="not-logged-in"' in resp.text
    assert 'id="dashboard"' in resp.text


def test_account_page_unknown_tenant_404(client: TestClient) -> None:
    resp = client.get("/nope/account")
    assert resp.status_code == 404


def test_account_page_reserved_slug_404(client: TestClient) -> None:
    resp = client.get("/login/account")
    assert resp.status_code == 404


def test_account_js_served(client: TestClient) -> None:
    resp = client.get("/static/js/account.js")
    assert resp.status_code == 200
    assert "PX.initAccount" in resp.text
    assert "/auth/me" in resp.text
    assert "/bookings" in resp.text


def test_tenant_header_shows_account_link(
    client: TestClient, sample_tenant: Tenant
) -> None:
    resp = client.get(f"/{sample_tenant.slug}/")
    assert resp.status_code == 200
    assert f"/{sample_tenant.slug}/account" in resp.text
    assert "My Account" in resp.text


def test_platform_header_hides_account_link(client: TestClient) -> None:
    """On platform-level pages (no tenant), account link should be hidden."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "My Account" not in resp.text
