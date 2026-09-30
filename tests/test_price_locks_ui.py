"""Tests for Price Locks UI page (Phase 47, Step 3)."""
from fastapi.testclient import TestClient


def test_price_locks_page_renders(client: TestClient) -> None:
    r = client.get("/account/price-locks")
    assert r.status_code == 200
    body = r.text
    assert "Price Locks" in body
    assert 'id="pl-body"' in body
    assert 'id="pl-refresh"' in body
    assert 'id="pl-show-all"' in body


def test_price_locks_page_calls_api(client: TestClient) -> None:
    r = client.get("/account/price-locks")
    body = r.text
    assert "/me/price-locks" in body
    assert "/me/price-locks/" in body  # delete path
