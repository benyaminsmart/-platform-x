"""Tests for AI location recommend UI on /search (Phase 45, Step 3)."""
from fastapi.testclient import TestClient


def test_search_page_has_ai_location_button(client: TestClient) -> None:
    r = client.get("/search")
    assert r.status_code == 200
    body = r.text
    assert 'id="sr-ai-loc"' in body
    assert 'id="sr-ai-loc-panel"' in body


def test_search_page_calls_ai_location_endpoint(client: TestClient) -> None:
    r = client.get("/search")
    body = r.text
    assert '/ai/location/recommend' in body
    assert 'sr-ai-loc-advice' in body


def test_search_page_ai_loc_uses_center_or_default(client: TestClient) -> None:
    r = client.get("/search")
    body = r.text
    # Falls back to Dubai center when map has no current center
    assert '25.2048' in body
    assert '55.2708' in body
