"""Tests for AI Trip Memory UI on /account/ai (Phase 46, Step 3)."""
from fastapi.testclient import TestClient


def test_account_ai_page_has_memory_button(client: TestClient) -> None:
    r = client.get("/account/ai")
    assert r.status_code == 200
    body = r.text
    assert 'id="open-memory"' in body
    assert 'id="trip-memory-panel"' in body


def test_account_ai_page_calls_memory_endpoint(client: TestClient) -> None:
    r = client.get("/account/ai")
    body = r.text
    assert '/account/api/ai/memory' in body
    assert 'memory-recap' in body
    assert 'memory-profile' in body
    assert 'memory-top-tenants' in body


def test_account_ai_page_has_close_memory(client: TestClient) -> None:
    r = client.get("/account/ai")
    body = r.text
    assert 'id="close-memory"' in body
