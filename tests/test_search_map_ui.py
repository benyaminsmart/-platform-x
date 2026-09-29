"""Tests: Map UI in /search (Phase 32, Step 3)."""
from fastapi.testclient import TestClient
from pathlib import Path


def test_search_page_has_map_elements(client: TestClient) -> None:
    r = client.get("/search")
    html = r.text
    assert 'id="sr-map"' in html
    assert 'id="sr-map-wrap"' in html
    assert 'id="sr-toggle-map"' in html
    assert 'id="sr-radius"' in html
    assert 'id="sr-clear-geo"' in html
    assert "leaflet" in html.lower()


def test_search_js_uses_geo_params() -> None:
    js = Path("app/templates/pages/search.html").read_text(encoding="utf-8")
    assert "currentCenter" in js
    assert "renderMarkers" in js
    assert "radius_km" in js
