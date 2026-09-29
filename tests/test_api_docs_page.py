"""Tests for Public API docs page (Phase 14, Step 7)."""

from fastapi.testclient import TestClient


def test_api_docs_renders(client: TestClient) -> None:
    r = client.get("/docs/api")
    assert r.status_code == 200
    html = r.text
    assert "Public API" in html
    assert "Authentication" in html
    assert "X-API-Key" in html


def test_api_docs_scopes_table(client: TestClient) -> None:
    r = client.get("/docs/api")
    html = r.text
    for scope in ["read:services", "read:bookings", "read:reviews",
                  "read:analytics", "write:webhooks"]:
        assert scope in html


def test_api_docs_endpoints_table(client: TestClient) -> None:
    r = client.get("/docs/api")
    html = r.text
    assert "/api/v1/me" in html
    assert "/api/v1/services" in html
    assert "/api/v1/bookings" in html
    assert "/api/v1/reviews" in html
    assert "/api/v1/analytics/summary" in html


def test_api_docs_has_code_examples(client: TestClient) -> None:
    r = client.get("/docs/api")
    html = r.text
    assert "import requests" in html
    assert "await fetch" in html
    assert "curl -sS" in html


def test_api_docs_has_webhook_signature_example(client: TestClient) -> None:
    r = client.get("/docs/api")
    html = r.text
    assert "X-PlatformX-Signature" in html
    assert "hmac" in html.lower()


def test_api_docs_has_error_table(client: TestClient) -> None:
    r = client.get("/docs/api")
    html = r.text
    assert "401" in html and "403" in html and "404" in html and "429" in html
