"""Tests for Auto-Repricing UI page (Phase 60, Step 3)."""
from fastapi.testclient import TestClient


def test_page_renders_title(client: TestClient) -> None:
    r = client.get("/business/auto-repricing")
    assert r.status_code == 200
    body = r.text
    assert "Auto-Repricing" in body


def test_page_has_ui_hooks(client: TestClient) -> None:
    r = client.get("/business/auto-repricing")
    body = r.text
    assert "ar-status-badge" in body
    assert "ar-toggle" in body
    assert "ar-preview" in body
    assert "ar-apply" in body
    assert "ar-service-id" in body


def test_page_calls_api(client: TestClient) -> None:
    r = client.get("/business/auto-repricing")
    body = r.text
    assert "/business/api/auto-repricing/status" in body
    assert "/business/api/auto-repricing/toggle" in body
    assert "/business/api/auto-repricing/preview" in body
    assert "/business/api/auto-repricing/apply" in body


def test_sidebar_link_present(client: TestClient) -> None:
    r = client.get("/business/dashboard")
    assert r.status_code == 200
    assert "/business/auto-repricing" in r.text
