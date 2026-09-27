"""End-to-end tests for service endpoints (admin uses real platform admin auth)."""

from fastapi.testclient import TestClient

from app.models.tenant import Tenant


def _service_payload(**overrides):
    base = {
        "type": "room",
        "name": "Deluxe Suite",
        "description": "Sea view",
        "price": "500.00",
        "currency": "AED",
        "capacity": 2,
        "attributes": {"bed": "king"},
        "image_urls": ["/img/1.jpg"],
        "display_order": 1,
    }
    base.update(overrides)
    return base


def _tenant_headers(tenant: Tenant) -> dict:
    return {"X-Tenant-Slug": tenant.slug}


def _admin_headers(tenant: Tenant, admin_client) -> dict:
    _, auth = admin_client
    return {"X-Tenant-Slug": tenant.slug, **auth}


def test_list_empty(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.get("/services", headers=_tenant_headers(sample_tenant))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_create_requires_admin(
    client: TestClient, sample_tenant: Tenant
) -> None:
    """Without admin token, POST should 401."""
    resp = client.post(
        "/services", json=_service_payload(), headers=_tenant_headers(sample_tenant)
    )
    assert resp.status_code == 401


def test_create_with_admin(
    client: TestClient, sample_tenant: Tenant, admin_client
) -> None:
    resp = client.post(
        "/services",
        json=_service_payload(),
        headers=_admin_headers(sample_tenant, admin_client),
    )
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["name"] == "Deluxe Suite"
    assert d["status"] == "active"
    assert d["attributes"]["bed"] == "king"
    assert d["image_urls"] == ["/img/1.jpg"]


def test_create_requires_super_admin_or_admin_role(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    """A 'support' role cannot create services."""
    from app.services import admin_service

    admin_service.create(
        db,
        email="support@example.com",
        password="SupportPass1234",
        name="Support",
        role="support",
    )
    r = client.post(
        "/platform/auth/login",
        json={"email": "support@example.com", "password": "SupportPass1234"},
    )
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

    resp = client.post(
        "/services",
        json=_service_payload(),
        headers={"X-Tenant-Slug": sample_tenant.slug, **auth},
    )
    assert resp.status_code == 403


def test_list_returns_created(
    client: TestClient, sample_tenant: Tenant, admin_client
) -> None:
    h = _admin_headers(sample_tenant, admin_client)
    client.post("/services", json=_service_payload(), headers=h)
    client.post("/services", json=_service_payload(name="Standard"), headers=h)

    resp = client.get("/services", headers=_tenant_headers(sample_tenant))
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_list_filter_by_type(
    client: TestClient, sample_tenant: Tenant, admin_client
) -> None:
    h = _admin_headers(sample_tenant, admin_client)
    client.post("/services", json=_service_payload(type="room"), headers=h)
    client.post("/services", json=_service_payload(type="dish", name="Kebab"), headers=h)

    resp = client.get(
        "/services?type=dish", headers=_tenant_headers(sample_tenant)
    )
    d = resp.json()
    assert d["total"] == 1
    assert d["items"][0]["type"] == "dish"


def test_get_detail(
    client: TestClient, sample_tenant: Tenant, admin_client
) -> None:
    h = _admin_headers(sample_tenant, admin_client)
    r = client.post("/services", json=_service_payload(), headers=h)
    sid = r.json()["id"]

    resp = client.get(
        f"/services/{sid}", headers=_tenant_headers(sample_tenant)
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == sid


def test_get_unknown_404(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.get("/services/nope", headers=_tenant_headers(sample_tenant))
    assert resp.status_code == 404


def test_update_partial(
    client: TestClient, sample_tenant: Tenant, admin_client
) -> None:
    h = _admin_headers(sample_tenant, admin_client)
    r = client.post("/services", json=_service_payload(), headers=h)
    sid = r.json()["id"]

    resp = client.patch(
        f"/services/{sid}",
        json={"price": "650.00", "name": "New Name"},
        headers=h,
    )
    assert resp.status_code == 200
    d = resp.json()
    assert d["price"] == "650.00"
    assert d["name"] == "New Name"


def test_update_requires_admin(
    client: TestClient, sample_tenant: Tenant, admin_client
) -> None:
    h = _admin_headers(sample_tenant, admin_client)
    r = client.post("/services", json=_service_payload(), headers=h)
    sid = r.json()["id"]

    resp = client.patch(
        f"/services/{sid}",
        json={"price": "1.00"},
        headers=_tenant_headers(sample_tenant),
    )
    assert resp.status_code == 401


def test_delete_soft(
    client: TestClient, sample_tenant: Tenant, admin_client
) -> None:
    h = _admin_headers(sample_tenant, admin_client)
    r = client.post("/services", json=_service_payload(), headers=h)
    sid = r.json()["id"]

    resp = client.delete(f"/services/{sid}", headers=h)
    assert resp.status_code == 200
    assert "deactivated" in resp.json()["message"]

    lst = client.get("/services", headers=_tenant_headers(sample_tenant))
    assert lst.json()["total"] == 0

    g = client.get(f"/services/{sid}", headers=_tenant_headers(sample_tenant))
    assert g.status_code == 404


def test_tenant_isolation(
    client: TestClient, sample_tenant: Tenant, admin_client, db
) -> None:
    """Services of tenant A are not visible to tenant B."""
    from app.models.tenant import Tenant as T

    other = T(slug="other", name="Other Co", tier="starter", status="active", config={})
    db.add(other)
    db.commit()

    h = _admin_headers(sample_tenant, admin_client)
    client.post("/services", json=_service_payload(), headers=h)

    resp = client.get("/services", headers={"X-Tenant-Slug": "other"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
