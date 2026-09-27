"""Tests for payment HTML page."""

from fastapi.testclient import TestClient

from app.models.tenant import Tenant


def test_pay_page_loads(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.get(f"/{sample_tenant.slug}/pay?booking=abc")
    assert resp.status_code == 200
    assert "Complete payment" in resp.text
    assert 'id="payment-panel"' in resp.text
    assert 'id="success-panel"' in resp.text


def test_pay_page_without_booking_still_loads(
    client: TestClient, sample_tenant: Tenant
) -> None:
    resp = client.get(f"/{sample_tenant.slug}/pay")
    assert resp.status_code == 200


def test_pay_page_unknown_tenant_404(client: TestClient) -> None:
    resp = client.get("/nope/pay?booking=abc")
    assert resp.status_code == 404


def test_pay_page_reserved_slug_404(client: TestClient) -> None:
    resp = client.get("/login/pay?booking=abc")
    assert resp.status_code == 404


def test_payment_js_served(client: TestClient) -> None:
    resp = client.get("/static/js/payment.js")
    assert resp.status_code == 200
    assert "PX.initPayment" in resp.text
    assert "/payments/intent" in resp.text
