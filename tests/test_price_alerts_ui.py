"""Tests for price alerts UI (Phase 43, Step 2)."""
from fastapi.testclient import TestClient
from pathlib import Path


def test_price_alerts_page_renders(client: TestClient) -> None:
    r = client.get("/account/price-alerts")
    assert r.status_code == 200
    html = r.text
    assert "Price Alerts" in html
    assert 'id="pa-body"' in html
    assert 'id="pa-check-btn"' in html
    assert "/me/price-alerts" in html


def test_search_has_watch_button(client: TestClient) -> None:
    r = client.get("/search")
    assert r.status_code == 200
    html = r.text
    assert "sr-watch-btn" in html
    assert "openWatchModal" in html
    assert "bindWatches" in html
