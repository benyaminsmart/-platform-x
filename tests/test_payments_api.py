"""End-to-end tests for payment endpoints."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.tenant import Tenant


def _auth(client: TestClient, tenant: Tenant, email: str = "payer@example.com") -> dict:
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Pass1234",
            "first_name": "Pay",
            "last_name": "Er",
        },
        headers={"X-Tenant-Slug": tenant.slug},
    )
    return {
        "X-Tenant-Slug": tenant.slug,
        "Authorization": f"Bearer {r.json()['access_token']}",
    }


def _create_booking(client: TestClient, h: dict, amount: str = "500.00") -> str:
    r = client.post(
        "/bookings",
        json={
            "booking_type": "room",
            "service_name": "Suite",
            "check_in": str(date.today() + timedelta(days=1)),
            "check_out": str(date.today() + timedelta(days=2)),
            "amount": amount,
            "currency": "AED",
        },
        headers=h,
    )
    return r.json()["id"]


def test_intent_for_booking_success(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _auth(client, sample_tenant)
    bid = _create_booking(client, h)
    resp = client.post(
        "/payments/intent",
        json={"booking_id": bid, "amount": "500.00", "currency": "AED", "method": "card"},
        headers=h,
    )
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["provider"] == "mock"
    assert d["status"] == "pending"
    assert d["provider_reference"].startswith("mock_")
    assert d["redirect_url"].startswith("/payments/mock/confirm/")


def test_intent_unknown_booking_400(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _auth(client, sample_tenant)
    resp = client.post(
        "/payments/intent",
        json={"booking_id": "nope", "amount": "10.00", "method": "card"},
        headers=h,
    )
    assert resp.status_code == 400


def test_intent_requires_auth(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.post(
        "/payments/intent",
        json={"booking_id": "x", "amount": "10.00", "method": "card"},
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert resp.status_code == 401


def test_get_payment_detail(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _auth(client, sample_tenant)
    bid = _create_booking(client, h)
    r = client.post(
        "/payments/intent",
        json={"booking_id": bid, "amount": "500.00", "method": "card"},
        headers=h,
    )
    pid = r.json()["payment_id"]

    resp = client.get(f"/payments/{pid}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_mock_confirm_flow_marks_paid(
    client: TestClient, sample_tenant: Tenant
) -> None:
    """End-to-end: intent → mock confirm → booking.payment_status = paid, status = confirmed."""
    h = _auth(client, sample_tenant)
    bid = _create_booking(client, h)
    r = client.post(
        "/payments/intent",
        json={"booking_id": bid, "amount": "500.00", "method": "card"},
        headers=h,
    )
    ref = r.json()["provider_reference"]
    pid = r.json()["payment_id"]

    # Confirm via mock URL
    c = client.get(f"/payments/mock/confirm/{ref}")
    assert c.status_code == 200
    assert c.json()["status"] == "success"

    # Payment is success
    p = client.get(f"/payments/{pid}", headers=h)
    assert p.json()["status"] == "success"
    assert p.json()["completed_at"] is not None

    # Booking updated
    b = client.get(f"/bookings/{bid}", headers=h)
    assert b.json()["payment_status"] == "paid"
    assert b.json()["status"] == "confirmed"


def test_mock_confirm_idempotent(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _auth(client, sample_tenant)
    bid = _create_booking(client, h)
    r = client.post(
        "/payments/intent",
        json={"booking_id": bid, "amount": "500.00", "method": "card"},
        headers=h,
    )
    ref = r.json()["provider_reference"]
    c1 = client.get(f"/payments/mock/confirm/{ref}")
    c2 = client.get(f"/payments/mock/confirm/{ref}")
    assert c1.status_code == 200
    assert c2.status_code == 200


def test_intent_for_paid_booking_rejected(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _auth(client, sample_tenant)
    bid = _create_booking(client, h)
    r = client.post(
        "/payments/intent",
        json={"booking_id": bid, "amount": "500.00", "method": "card"},
        headers=h,
    )
    ref = r.json()["provider_reference"]
    client.get(f"/payments/mock/confirm/{ref}")

    # Now try a second intent on the same booking
    resp = client.post(
        "/payments/intent",
        json={"booking_id": bid, "amount": "500.00", "method": "card"},
        headers=h,
    )
    assert resp.status_code == 400


def test_webhook_success_and_failure(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _auth(client, sample_tenant)
    # Success webhook
    bid = _create_booking(client, h, amount="100.00")
    r = client.post(
        "/payments/intent",
        json={"booking_id": bid, "amount": "100.00", "method": "card"},
        headers=h,
    )
    ref1 = r.json()["provider_reference"]

    wh = client.post(
        "/payments/webhook/mock",
        json={"provider_reference": ref1, "status": "success"},
    )
    assert wh.status_code == 200
    assert wh.json()["payment_status"] == "success"

    # Failure webhook
    bid2 = _create_booking(client, h, amount="200.00")
    r2 = client.post(
        "/payments/intent",
        json={"booking_id": bid2, "amount": "200.00", "method": "card"},
        headers=h,
    )
    ref2 = r2.json()["provider_reference"]
    wh2 = client.post(
        "/payments/webhook/mock",
        json={"provider_reference": ref2, "status": "failed"},
    )
    assert wh2.status_code == 200
    assert wh2.json()["payment_status"] == "failed"


def test_webhook_invalid_status_400(client: TestClient) -> None:
    resp = client.post(
        "/payments/webhook/mock",
        json={"provider_reference": "x", "status": "nonsense"},
    )
    assert resp.status_code == 400


def test_webhook_unknown_reference_ok(client: TestClient) -> None:
    resp = client.post(
        "/payments/webhook/mock",
        json={"provider_reference": "unknown_ref", "status": "success"},
    )
    assert resp.status_code == 200
    assert resp.json()["unknown_reference"] is True


def test_intent_for_order_success(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _auth(client, sample_tenant)
    r = client.post(
        "/orders",
        json={
            "service_type": "dining",
            "service_name": "Lunch",
            "quantity": 1,
            "amount": "60.00",
        },
        headers=h,
    )
    oid = r.json()["id"]

    resp = client.post(
        "/payments/intent",
        json={"order_id": oid, "amount": "60.00", "method": "card"},
        headers=h,
    )
    assert resp.status_code == 201
    # confirm and check order
    ref = resp.json()["provider_reference"]
    client.get(f"/payments/mock/confirm/{ref}")
    o = client.get(f"/orders/{oid}", headers=h)
    assert o.json()["payment_status"] == "paid"
