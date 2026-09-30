"""Tests for Lock button on /search cards (Phase 47, Step 4)."""
from fastapi.testclient import TestClient


def test_search_page_has_lock_button(client: TestClient) -> None:
    r = client.get("/search")
    assert r.status_code == 200
    body = r.text
    assert "sr-lock-btn" in body
    assert "🔒 Lock" in body


def test_search_page_has_lock_modal(client: TestClient) -> None:
    r = client.get("/search")
    body = r.text
    assert "openLockModal" in body
    assert "/me/price-locks" in body


def test_search_page_calls_bind_locks(client: TestClient) -> None:
    r = client.get("/search")
    body = r.text
    # bindWatches must call the lock binder
    assert 'querySelectorAll(".sr-lock-btn")' in body
