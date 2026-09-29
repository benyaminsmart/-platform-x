"""Tests: compare UI (Phase 33, Step 5b)."""
from fastapi.testclient import TestClient


def test_compare_page_renders(client: TestClient) -> None:
    r = client.get("/compare")
    assert r.status_code == 200
    assert "Compare experiences" in r.text
    assert 'id="cmp-body"' in r.text
    assert "/api/compare" in r.text


def test_search_has_compare_button(client: TestClient) -> None:
    r = client.get("/search")
    html = r.text
    assert "sr-compare-btn" in html
    assert "toggleCompare" in html
    assert "/compare?ids=" in html
