"""Tests for the public /leaderboard HTML page (Phase 29, Step 6)."""

from fastapi.testclient import TestClient


def test_leaderboard_page_renders(client: TestClient) -> None:
    r = client.get("/leaderboard")
    assert r.status_code == 200
    html = r.text
    assert "Business Leaderboard" in html
    assert "px-lb-tabs" in html
    assert "px-lb-tab" in html
    # Category tabs
    assert 'data-cat="hotels"' in html
    assert 'data-cat="restaurants"' in html
    assert 'data-cat="travel"' in html
    assert 'data-cat="entertainment"' in html
    # Body container
    assert 'id="lb-body"' in html


def test_leaderboard_page_calls_correct_api(client: TestClient) -> None:
    r = client.get("/leaderboard")
    html = r.text
    # Page fetches from /api/leaderboard (not /leaderboard)
    assert '"/api/leaderboard"' in html


def test_api_leaderboard_endpoint_returns_json(client: TestClient) -> None:
    """The /api/leaderboard endpoint must return JSON, not HTML."""
    r = client.get("/api/leaderboard")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert isinstance(r.json(), list)


def test_html_and_api_paths_are_distinct(client: TestClient) -> None:
    """Regression: /leaderboard must serve HTML, /api/leaderboard must serve JSON."""
    html = client.get("/leaderboard")
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")

    api = client.get("/api/leaderboard")
    assert api.status_code == 200
    assert api.headers["content-type"].startswith("application/json")
