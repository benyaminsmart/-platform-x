"""Tests for rate plans page (Phase 37, Step 4)."""
from fastapi.testclient import TestClient


def test_rate_plans_page_renders(client: TestClient) -> None:
    r = client.get("/business/rate-plans")
    assert r.status_code == 200
    html = r.text
    assert "Rate Plans" in html
    assert 'id="rp-list"' in html
    assert 'id="rp-modal"' in html
    assert 'id="rp-new-btn"' in html


def test_rate_plans_sidebar_link(client: TestClient) -> None:
    r = client.get("/business/rate-plans")
    assert 'href="/business/rate-plans"' in r.text
    assert "is-active" in r.text


def test_rate_plans_page_apis(client: TestClient) -> None:
    r = client.get("/business/rate-plans")
    html = r.text
    assert "/business/api/rate-plans" in html
    assert "/business/api/services" in html
