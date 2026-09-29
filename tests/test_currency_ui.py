"""Tests: currency dropdown in /search page (Phase 30, Step 6c)."""
from pathlib import Path
from fastapi.testclient import TestClient


def test_search_page_has_currency_dropdown(client: TestClient) -> None:
    r = client.get("/search")
    assert r.status_code == 200
    html = r.text
    assert 'id="sr-cur"' in html
    assert 'value="USD"' in html
    assert 'value="EUR"' in html


def test_search_js_reads_currency_param() -> None:
    js = Path("app/templates/pages/search.html").read_text(encoding="utf-8")
    assert 'u.get("currency")' in js
    assert "currency_note" in js
