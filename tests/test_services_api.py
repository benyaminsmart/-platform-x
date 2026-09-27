"""End-to-end tests for service endpoints."""

from fastapi.testclient import TestClient

from app.models.tenant import Tenant

ADMIN = {"X-Admin-Key": "dev-admin-key"}


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


def _headers(tenant: Tenant, admin: bool = False) -> dict:
    h = {"X-Tenant-Slug": tenant.slug}
    if admin:
        h.update(ADMIN)
    return h


def test_list_empty(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.get("/services", headers=_headers(sample_tenant))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_create_requires_admin_key(
    client: TestClient, sample_tenant: Tenant
) -> None:
    resp = client.post(
        "/services", json=_service_payload(), headers=_headers(sample_tenant)
    )
    assert resp.status_code == 403


def test_create_with_admin_key(
    client: TestClient, sample_tenant: Tenant
) -> None:
    resp = client.post(
        "/services",
        json=_service_payload(),
        headers=_headers(sample_tenant, admin=True),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "Deluxe Suite"
    assert data["status"] == "active"
    assert data["attributes"]["bed"] == "king"
    assert data["image_urls"] == ["/img/1.jpg"]


def test_list_returns_created(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _headers(sample_tenant, admin=True)
    client.post("/services", json=_service_payload(), headers=h)
    client.post("/services", json=_service_payload(name="Standard"), headers=h)

    resp = client.get("/services", headers=_headers(sample_tenant))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


def test_list_filter_by_type(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _headers(sample_tenant, admin=True)
    client.post("/services", json=_service_payload(type="room"), headers=h)
    client.post("/services", json=_service_payload(type="dish", name="Kebab"), headers=h)

    resp = client.get("/services?type=dish", headers=_headers(sample_tenant))
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["type"] == "dish"


def test_get_detail(client: TestClient, sample_tenant: Tenant) -> None:
    h = _headers(sample_tenant, admin=True)
    r = client.post("/services", json=_service_payload(), headers=h)
    sid = r.json()["id"]

    resp = client.get(f"/services/{sid}", headers=_headers(sample_tenant))
    assert resp.status_code == 200
    assert resp.json()["id"] == sid


def test_get_unknown_404(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.get("/services/nope", headers=_headers(sample_tenant))
    assert resp.status_code == 404


def test_update_partial(client: TestClient, sample_tenant: Tenant) -> None:
    h = _headers(sample_tenant, admin=True)
    r = client.post("/services", json=_service_payload(), headers=h)
    sid = r.json()["id"]

    resp = client.patch(
        f"/services/{sid}", json={"price": "650.00", "name": "New Name"}, headers=h
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["price"] == "650.00"
    assert data["name"] == "New Name"


def test_update_requires_admin(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h_admin = _headers(sample_tenant, admin=True)
    r = client.post("/services", json=_service_payload(), headers=h_admin)
    sid = r.json()["id"]

    resp = client.patch(
        f"/services/{sid}", json={"price": "1.00"}, headers=_headers(sample_tenant)
    )
    assert resp.status_code == 403


def test_delete_soft(client: TestClient, sample_tenant: Tenant) -> None:
    h = _headers(sample_tenant, admin=True)
    r = client.post("/services", json=_service_payload(), headers=h)
    sid = r.json()["id"]

    resp = client.delete(f"/services/{sid}", headers=h)
    assert resp.status_code == 200
    assert "deactivated" in resp.json()["message"]

    # No longer in public list
    lst = client.get("/services", headers=_headers(sample_tenant))
    assert lst.json()["total"] == 0

    # But GET by id should 404 (status != active)
    g = client.get(f"/services/{sid}", headers=_headers(sample_tenant))
    assert g.status_code == 404


def test_tenant_isolation(client: TestClient, sample_tenant: Tenant, db) -> None:
    """Services of tenant A are not visible to tenant B."""
    from app.models.tenant import Tenant as T

    other = T(slug="other", name="Other Co", tier="starter", status="active", config={})
    db.add(other)
    db.commit()

    h_a = _headers(sample_tenant, admin=True)
    client.post("/services", json=_service_payload(), headers=h_a)

    resp = client.get("/services", headers={"X-Tenant-Slug": "other"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
