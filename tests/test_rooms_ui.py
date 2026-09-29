"""Tests for rooms page (Phase 36, Step 3)."""
from fastapi.testclient import TestClient


def test_rooms_page_renders(client: TestClient) -> None:
    r = client.get("/business/rooms")
    assert r.status_code == 200
    html = r.text
    assert "Rooms" in html
    assert 'id="rm-list"' in html
    assert 'id="rm-modal"' in html
    assert 'id="rm-new-btn"' in html


def test_rooms_sidebar_link(client: TestClient) -> None:
    r = client.get("/business/rooms")
    assert 'href="/business/rooms"' in r.text
    assert "is-active" in r.text


def test_rooms_page_apis(client: TestClient) -> None:
    r = client.get("/business/rooms")
    html = r.text
    assert "/business/api/rooms" in html
    assert "/business/api/services" in html
    assert "/business/api/me" in html
