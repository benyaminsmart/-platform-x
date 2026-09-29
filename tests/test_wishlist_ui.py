"""Tests: wishlist heart in /search (Phase 33, Step 3)."""
from fastapi.testclient import TestClient
from pathlib import Path


def test_search_page_has_heart_css(client: TestClient) -> None:
    r = client.get("/search")
    html = r.text
    assert "sr-heart" in html
    assert "bindHearts" in html


def test_search_js_uses_wishlist_endpoints() -> None:
    js = Path("app/templates/pages/search.html").read_text(encoding="utf-8")
    assert "/wishlist" in js
    assert "toggleHeart" in js
