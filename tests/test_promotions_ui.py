"""Tests for promotions page (Phase 38, Step 5)."""
from fastapi.testclient import TestClient


def test_promotions_page_renders(client: TestClient) -> None:
    r = client.get("/business/promotions")
    assert r.status_code == 200
    html = r.text
    assert "Promotions" in html
    assert 'id="pr-list"' in html
    assert 'id="pr-new-btn"' in html


def test_promotions_sidebar_link(client: TestClient) -> None:
    r = client.get("/business/promotions")
    assert 'href="/business/promotions"' in r.text
    assert "is-active" in r.text


def test_promotions_page_apis(client: TestClient) -> None:
    r = client.get("/business/promotions")
    assert "/business/api/promotions" in r.text
    assert "/business/api/me" in r.text
