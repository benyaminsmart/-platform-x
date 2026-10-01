"""Tests for Bundle Deals UI on /search (Phase 51, Step 3)."""
from fastapi.testclient import TestClient


def test_search_page_has_bundle_button(client: TestClient) -> None:
    r = client.get("/search")
    assert r.status_code == 200
    body = r.text
    assert 'id="sr-bundle"' in body
    assert 'id="sr-bundle-panel"' in body
    assert 'Bundle this trip' in body


def test_search_page_calls_bundle_endpoint(client: TestClient) -> None:
    r = client.get("/search")
    body = r.text
    assert "/api/bundle-deals" in body
    assert 'id="sr-bundle-advice"' in body
    assert 'id="sr-bundle-items"' in body
    assert 'id="sr-bundle-close"' in body
