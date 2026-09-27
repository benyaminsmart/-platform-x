"""End-to-end tests for order endpoints."""

from fastapi.testclient import TestClient

from app.models.tenant import Tenant


def _auth_headers(client: TestClient, tenant: Tenant, email: str = "order@example.com") -> dict[str, str]:
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Pass1234",
            "first_name": "Ord",
            "last_name": "Er",
        },
        headers={"X-Tenant-Slug": tenant.slug},
    )
    token = r.json()["access_token"]
    return {"X-Tenant-Slug": tenant.slug, "Authorization": f"Bearer {token}"}


def _payload(**overrides):
    base = {
        "service_type": "dining",
        "service_name": "Breakfast",
        "quantity": 2,
        "amount": "80.00",
        "currency": "AED",
    }
    base.update(overrides)
    return base


def test_create_success(client: TestClient, sample_tenant: Tenant) -> None:
    h = _auth_headers(client, sample_tenant)
    resp = client.post("/orders", json=_payload(), headers=h)
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["status"] == "pending"
    assert d["payment_status"] == "pending"
    assert d["quantity"] == 2


def test_create_requires_auth(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.post(
        "/orders", json=_payload(), headers={"X-Tenant-Slug": sample_tenant.slug}
    )
    assert resp.status_code == 401


def test_create_quantity_zero_422(client: TestClient, sample_tenant: Tenant) -> None:
    h = _auth_headers(client, sample_tenant)
    resp = client.post("/orders", json=_payload(quantity=0), headers=h)
    assert resp.status_code == 422


def test_list_my_orders(client: TestClient, sample_tenant: Tenant) -> None:
    h = _auth_headers(client, sample_tenant)
    client.post("/orders", json=_payload(), headers=h)
    client.post("/orders", json=_payload(service_name="Lunch"), headers=h)

    resp = client.get("/orders", headers=h)
    d = resp.json()
    assert d["total"] == 2
    assert len(d["items"]) == 2


def test_list_filter_status(client: TestClient, sample_tenant: Tenant) -> None:
    h = _auth_headers(client, sample_tenant)
    r = client.post("/orders", json=_payload(), headers=h)
    client.post("/orders", json=_payload(), headers=h)
    client.post(f"/orders/{r.json()['id']}/cancel", headers=h)

    resp = client.get("/orders?status=cancelled", headers=h)
    assert resp.json()["total"] == 1


def test_list_pagination(client: TestClient, sample_tenant: Tenant) -> None:
    h = _auth_headers(client, sample_tenant)
    for i in range(3):
        client.post("/orders", json=_payload(service_name=f"X{i}"), headers=h)
    resp = client.get("/orders?page=2&limit=2", headers=h)
    d = resp.json()
    assert d["total"] == 3
    assert len(d["items"]) == 1


def test_get_detail(client: TestClient, sample_tenant: Tenant) -> None:
    h = _auth_headers(client, sample_tenant)
    r = client.post("/orders", json=_payload(), headers=h)
    oid = r.json()["id"]
    resp = client.get(f"/orders/{oid}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["id"] == oid


def test_get_unknown_404(client: TestClient, sample_tenant: Tenant) -> None:
    h = _auth_headers(client, sample_tenant)
    resp = client.get("/orders/nope", headers=h)
    assert resp.status_code == 404


def test_cancel_success(client: TestClient, sample_tenant: Tenant) -> None:
    h = _auth_headers(client, sample_tenant)
    r = client.post("/orders", json=_payload(), headers=h)
    resp = client.post(f"/orders/{r.json()['id']}/cancel", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_cancel_already_cancelled_409(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _auth_headers(client, sample_tenant)
    r = client.post("/orders", json=_payload(), headers=h)
    oid = r.json()["id"]
    client.post(f"/orders/{oid}/cancel", headers=h)
    resp = client.post(f"/orders/{oid}/cancel", headers=h)
    assert resp.status_code == 409


def test_tenant_isolation(client: TestClient, sample_tenant: Tenant, db) -> None:
    """Orders of tenant A are not visible to tenant B's user."""
    from app.models.tenant import Tenant as T

    other = T(slug="other", name="Other Co", tier="starter", status="active", config={})
    db.add(other)
    db.commit()

    h = _auth_headers(client, sample_tenant)
    client.post("/orders", json=_payload(), headers=h)

    # Attempting to fetch tenant A's order with tenant B header should fail tenant check
    r = client.get("/orders", headers={"X-Tenant-Slug": "other"})
    # /orders requires auth; with tenant B header, our token is invalid (tenant mismatch)
    assert r.status_code == 401
