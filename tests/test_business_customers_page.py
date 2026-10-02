"""Tests for Business Customers page polish (Phase 66, Step 2)."""
from fastapi.testclient import TestClient


def test_customers_page_renders_title(client: TestClient) -> None:
    r = client.get("/business/customers")
    assert r.status_code == 200
    assert "Customers" in r.text


def test_customers_page_uses_adm_tokens(client: TestClient) -> None:
    """Phase 66 goal: template must use --adm-* design tokens."""
    r = client.get("/business/customers")
    body = r.text
    assert "--adm-" in body
    assert "cu-table" in body
    assert "cu-refresh" in body


def test_customers_page_calls_api(client: TestClient) -> None:
    r = client.get("/business/customers")
    body = r.text
    assert "/business/api/customers" in body
