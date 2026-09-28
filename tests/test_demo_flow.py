"""End-to-end test simulating the demo user journey.

This validates the full pipeline: browse services -> register -> book ->
pay -> booking confirmed -> rewards tracked.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.tenant import Tenant
from app.services import service_service


def test_full_demo_journey(client: TestClient, sample_tenant: Tenant, db) -> None:
    # 1. Browse public services (empty initially)
    r = client.get(
        "/services", headers={"X-Tenant-Slug": sample_tenant.slug}
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0

    # 2. Admin creates a room service
    from app.services import admin_service

    admin_service.create(
        db, email="demo-admin@x.com", password="AdminPass1234", name="A", role="super_admin"
    )
    login = client.post(
        "/platform/auth/login",
        json={"email": "demo-admin@x.com", "password": "AdminPass1234"},
    )
    admin_h = {
        "X-Tenant-Slug": sample_tenant.slug,
        "Authorization": f"Bearer {login.json()['access_token']}",
    }
    svc_resp = client.post(
        "/services",
        json={
            "type": "room",
            "name": "Demo Room",
            "price": "500.00",
            "capacity": 2,
        },
        headers=admin_h,
    )
    assert svc_resp.status_code == 201
    service_id = svc_resp.json()["id"]

    # 3. Public sees it
    r = client.get("/services", headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["name"] == "Demo Room"

    # 4. Guest registers
    reg = client.post(
        "/auth/register",
        json={
            "email": "guest@x.com",
            "password": "GuestPass123",
            "first_name": "Guest",
            "last_name": "One",
        },
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert reg.status_code == 201
    user_h = {
        "X-Tenant-Slug": sample_tenant.slug,
        "Authorization": f"Bearer {reg.json()['access_token']}",
    }

    # 5. Track a page_view event
    ev = client.post(
        "/analytics/events",
        json={"event_type": "booking_started", "metadata": {"service": service_id}},
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert ev.status_code == 201

    # 6. Create booking
    bk = client.post(
        "/bookings",
        json={
            "booking_type": "room",
            "service_id": service_id,
            "service_name": "Demo Room",
            "check_in": str(date.today() + timedelta(days=1)),
            "check_out": str(date.today() + timedelta(days=2)),
            "guests": 2,
            "amount": "500.00",
        },
        headers=user_h,
    )
    assert bk.status_code == 201
    booking_id = bk.json()["id"]
    assert bk.json()["status"] == "pending"
    assert bk.json()["payment_status"] == "pending"

    # 7. Create payment intent
    pi = client.post(
        "/payments/intent",
        json={"booking_id": booking_id, "amount": "500.00", "method": "card"},
        headers=user_h,
    )
    assert pi.status_code == 201
    ref = pi.json()["provider_reference"]

    # 8. Confirm (mock gateway)
    cf = client.get(f"/payments/mock/confirm/{ref}")
    assert cf.status_code == 200

    # 9. Verify booking now confirmed + paid
    bk2 = client.get(f"/bookings/{booking_id}", headers=user_h)
    assert bk2.json()["status"] == "confirmed"
    assert bk2.json()["payment_status"] == "paid"

    # 10. Notifications are now created automatically (welcome + booking)
    notifs = client.get("/notifications", headers=user_h)
    assert notifs.json()["total"] >= 1
    templates = [n["template"] for n in notifs.json()["items"]]
    assert "booking_confirmed" in templates

    # 11. Analytics summary shows the tracked event
    summary = client.get("/analytics/summary", headers=admin_h)
    assert summary.json()["total_events"] == 1


def test_seed_services_for_sample_tenant(client: TestClient, sample_tenant: Tenant, db) -> None:
    """Confirm service_service.create handles seeds correctly."""
    from decimal import Decimal
    from app.schemas.service import ServiceCreate

    service_service.create_service(
        db,
        tenant_id=sample_tenant.id,
        payload=ServiceCreate(type="room", name="S1", price=Decimal("100")),
    )
    service_service.create_service(
        db,
        tenant_id=sample_tenant.id,
        payload=ServiceCreate(type="room", name="S2", price=Decimal("200")),
    )
    r = client.get("/services", headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.json()["total"] == 2
