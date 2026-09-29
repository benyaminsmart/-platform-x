"""Tests: wishlist page (Phase 33, Step 4)."""
from fastapi.testclient import TestClient


def test_wishlist_page_renders(client: TestClient) -> None:
    r = client.get("/account/wishlist")
    assert r.status_code == 200
    html = r.text
    assert "My Wishlist" in html
    assert 'id="wl-body"' in html


def test_wishlist_page_calls_api(client: TestClient) -> None:
    r = client.get("/account/wishlist")
    assert "/wishlist" in r.text
    assert "data-remove" in r.text
