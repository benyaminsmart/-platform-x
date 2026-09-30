"""Tests for Waitlist UI page (Phase 48, Step 3)."""
from fastapi.testclient import TestClient


def test_waitlist_page_renders(client: TestClient) -> None:
    r = client.get("/account/waitlist")
    assert r.status_code == 200
    body = r.text
    assert "Smart Waitlist" in body
    assert 'id="wl-body"' in body
    assert 'id="wl-refresh"' in body
    assert 'id="wl-show-all"' in body


def test_waitlist_page_calls_api(client: TestClient) -> None:
    r = client.get("/account/waitlist")
    body = r.text
    assert "/me/waitlist" in body
    assert "/me/waitlist/" in body  # delete path
