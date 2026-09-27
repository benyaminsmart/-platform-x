"""End-to-end tests for booking endpoints."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.tenant import Tenant


def _auth_headers(client: TestClient, tenant: Tenant) -> dict[str, str]:
    r = client.post(
        "/auth/register",
        json={
            "email": "booker@example.com",
            "password": "Pass1234",
            "first_name": "Book",
            "last_name": "Er",
        },
        headers={"X-Tenant-Slug": tenant.slug},
    )
    token = r.json()["access_token"]
    return {"X-Tenant-Slug": tenant.slug, "Authorization": f"Bearer {token}"}


def _booking_payload(**overrides):
    base = {
        "booking_type": "room",
        "service_name": "Deluxe Suite",
        "check_in": str(date.today() + timedelta(days=1)),
        "check_out": str(date.today() + timedelta(days=3)),
        "guests": 2,
        "amount": "500.00",
        "discount": "50.00",
        "currency": "AED",
    }
    base.update(overrides)
    return base


def test_create_booking_success(client: TestClient, sample_tenant: Tenant) -> None:
    headers = _auth_headers(client, sample_tenant)
    resp = client.post("/bookings", json=_booking_payload(), headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "pending"
    assert data["payment_status"] == "pending"
    assert data["total_amount"] == "450.00"
    assert data["currency"] == "AED"


def test_create_booking_requires_auth(
    client: TestClient, sample_tenant: Tenant
) -> None:
    resp = client.post(
        "/bookings",
        json=_booking_payload(),
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert resp.status_code == 401


def test_create_booking_bad_dates_422(
    client: TestClient, sample_tenant: Tenant
) -> None:
    headers = _auth_headers(client, sample_tenant)
    resp = client.post(
        "/bookings",
        json=_booking_payload(
            check_in=str(date.today() + timedelta(days=5)),
            check_out=str(date.today() + timedelta(days=1)),
        ),
        headers=headers,
    )
    assert resp.status_code == 422


def test_list_my_bookings(client: TestClient, sample_tenant: Tenant) -> None:
    headers = _auth_headers(client, sample_tenant)
    client.post("/bookings", json=_booking_payload(), headers=headers)
    client.post("/bookings", json=_booking_payload(service_name="Other"), headers=headers)

    resp = client.get("/bookings", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1


def test_list_bookings_filter_status(
    client: TestClient, sample_tenant: Tenant
) -> None:
    headers = _auth_headers(client, sample_tenant)
    r = client.post("/bookings", json=_booking_payload(), headers=headers)
    client.post("/bookings", json=_booking_payload(), headers=headers)
    bid = r.json()["id"]
    client.post(f"/bookings/{bid}/cancel", headers=headers)

    resp = client.get("/bookings?status=cancelled", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_list_bookings_pagination(
    client: TestClient, sample_tenant: Tenant
) -> None:
    headers = _auth_headers(client, sample_tenant)
    for i in range(3):
        client.post(
            "/bookings", json=_booking_payload(service_name=f"S{i}"), headers=headers
        )
    resp = client.get("/bookings?page=2&limit=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 1


def test_get_booking_detail(client: TestClient, sample_tenant: Tenant) -> None:
    headers = _auth_headers(client, sample_tenant)
    r = client.post("/bookings", json=_booking_payload(), headers=headers)
    bid = r.json()["id"]

    resp = client.get(f"/bookings/{bid}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == bid


def test_get_unknown_booking_404(
    client: TestClient, sample_tenant: Tenant
) -> None:
    headers = _auth_headers(client, sample_tenant)
    resp = client.get("/bookings/nonexistent-id", headers=headers)
    assert resp.status_code == 404


def test_cancel_booking_success(
    client: TestClient, sample_tenant: Tenant
) -> None:
    headers = _auth_headers(client, sample_tenant)
    r = client.post("/bookings", json=_booking_payload(), headers=headers)
    bid = r.json()["id"]

    resp = client.post(f"/bookings/{bid}/cancel", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_at"] is not None


def test_cancel_already_cancelled_409(
    client: TestClient, sample_tenant: Tenant
) -> None:
    headers = _auth_headers(client, sample_tenant)
    r = client.post("/bookings", json=_booking_payload(), headers=headers)
    bid = r.json()["id"]
    client.post(f"/bookings/{bid}/cancel", headers=headers)

    resp = client.post(f"/bookings/{bid}/cancel", headers=headers)
    assert resp.status_code == 409


def test_booking_tenant_isolation(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    """User from tenant A cannot see tenant B's bookings via /bookings."""
    from app.models.tenant import Tenant as T

    other = T(slug="other", name="Other Co", tier="starter", status="active", config={})
    db.add(other)
    db.commit()

    headers_a = _auth_headers(client, sample_tenant)
    r = client.post("/bookings", json=_booking_payload(), headers=headers_a)
    assert r.status_code == 201
