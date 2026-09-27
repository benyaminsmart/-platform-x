"""End-to-end tests for auth endpoints."""

from fastapi.testclient import TestClient

from app.models.tenant import Tenant


def _register_payload(**overrides):
    base = dict(
        email="guest@example.com",
        password="Pass1234",
        first_name="Ali",
        last_name="Karimi",
    )
    base.update(overrides)
    return base


def test_register_success(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.post(
        "/auth/register",
        json=_register_payload(),
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_register_duplicate_email_conflict(
    client: TestClient, sample_tenant: Tenant
) -> None:
    headers = {"X-Tenant-Slug": sample_tenant.slug}
    client.post("/auth/register", json=_register_payload(), headers=headers)
    resp = client.post("/auth/register", json=_register_payload(), headers=headers)
    assert resp.status_code == 409


def test_register_unknown_tenant_404(client: TestClient) -> None:
    resp = client.post(
        "/auth/register",
        json=_register_payload(),
        headers={"X-Tenant-Slug": "nope"},
    )
    assert resp.status_code == 404


def test_register_weak_password_422(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.post(
        "/auth/register",
        json=_register_payload(password="short"),
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert resp.status_code == 422


def test_login_success(client: TestClient, sample_tenant: Tenant) -> None:
    headers = {"X-Tenant-Slug": sample_tenant.slug}
    client.post("/auth/register", json=_register_payload(), headers=headers)
    resp = client.post(
        "/auth/login",
        json={"email": "guest@example.com", "password": "Pass1234"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_401(
    client: TestClient, sample_tenant: Tenant
) -> None:
    headers = {"X-Tenant-Slug": sample_tenant.slug}
    client.post("/auth/register", json=_register_payload(), headers=headers)
    resp = client.post(
        "/auth/login",
        json={"email": "guest@example.com", "password": "WrongPass1"},
        headers=headers,
    )
    assert resp.status_code == 401


def test_login_unknown_email_401(
    client: TestClient, sample_tenant: Tenant
) -> None:
    resp = client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "Pass1234"},
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert resp.status_code == 401


def test_me_success(client: TestClient, sample_tenant: Tenant) -> None:
    headers = {"X-Tenant-Slug": sample_tenant.slug}
    r = client.post("/auth/register", json=_register_payload(), headers=headers)
    token = r.json()["access_token"]
    resp = client.get(
        "/auth/me",
        headers={**headers, "Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "guest@example.com"
    assert data["tenant_id"] == sample_tenant.id


def test_me_without_token_401(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.get(
        "/auth/me",
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert resp.status_code == 401


def test_me_with_invalid_token_401(
    client: TestClient, sample_tenant: Tenant
) -> None:
    resp = client.get(
        "/auth/me",
        headers={
            "X-Tenant-Slug": sample_tenant.slug,
            "Authorization": "Bearer not-a-real-token",
        },
    )
    assert resp.status_code == 401


def test_token_works_across_tenants(client: TestClient, sample_tenant: Tenant, db) -> None:
    """Users are platform-wide: a token issued on one tenant works on all."""
    from app.models.tenant import Tenant as T

    other = T(slug="other", name="Other Co", tier="starter", status="active", config={})
    db.add(other)
    db.commit()

    r = client.post(
        "/auth/register",
        json=_register_payload(),
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    token = r.json()["access_token"]

    resp = client.get(
        "/auth/me",
        headers={"X-Tenant-Slug": "other", "Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "guest@example.com"
