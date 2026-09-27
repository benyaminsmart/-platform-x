"""Tests for booking HTML page."""

from fastapi.testclient import TestClient

from app.models.service import Service
from app.models.tenant import Tenant


def test_booking_page_loads(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    db.add(Service(
        tenant_id=sample_tenant.id, type="room", name="Test Room", price=500
    ))
    db.commit()

    resp = client.get(f"/{sample_tenant.slug}/book")
    assert resp.status_code == 200
    assert "Make a booking" in resp.text
    assert 'id="booking-form"' in resp.text
    assert "Test Room" in resp.text


def test_booking_page_preselects_service(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    s = Service(tenant_id=sample_tenant.id, type="room", name="Preselect", price=100)
    db.add(s)
    db.commit()

    resp = client.get(f"/{sample_tenant.slug}/book?service={s.id}")
    assert resp.status_code == 200
    assert "selected" in resp.text


def test_booking_page_unknown_tenant_404(client: TestClient) -> None:
    resp = client.get("/nope/book")
    assert resp.status_code == 404


def test_booking_page_reserved_slug_404(client: TestClient) -> None:
    resp = client.get("/login/book")
    assert resp.status_code == 404


def test_booking_js_served(client: TestClient) -> None:
    resp = client.get("/static/js/booking.js")
    assert resp.status_code == 200
    assert "PX.initBooking" in resp.text
