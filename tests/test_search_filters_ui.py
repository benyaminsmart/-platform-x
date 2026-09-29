"""Tests: extra filters in /search UI (Phase 30, Step 9b)."""
from fastapi.testclient import TestClient
from pathlib import Path


def test_search_page_has_extra_filters(client: TestClient) -> None:
    r = client.get("/search")
    html = r.text
    assert 'id="sr-loc"' in html
    assert 'id="sr-rating"' in html
    assert 'name="location"' in html
    assert 'name="min_rating"' in html


def test_search_js_reads_new_params() -> None:
    js = Path("app/templates/pages/search.html").read_text(encoding="utf-8")
    assert 'u.get("location")' in js
    assert 'u.get("min_rating")' in js
