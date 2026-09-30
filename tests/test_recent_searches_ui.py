"""Tests for recent searches UI (Phase 42, Step 2)."""
from fastapi.testclient import TestClient
from pathlib import Path


def test_search_page_has_recent(client: TestClient) -> None:
    r = client.get("/search")
    assert r.status_code == 200
    html = r.text
    assert 'id="sr-recent"' in html
    assert 'id="sr-recent-list"' in html
    assert 'id="sr-recent-clear"' in html


def test_search_js_uses_recent_api() -> None:
    js = Path("app/templates/pages/search.html").read_text(encoding="utf-8")
    assert "/me/recent-searches" in js
    assert "saveRecent" in js
    assert "loadRecent" in js
    assert "describeRecent" in js
