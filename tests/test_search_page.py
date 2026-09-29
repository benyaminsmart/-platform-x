"""Tests for /search HTML page + home form (Phase 30, Step 3)."""
from fastapi.testclient import TestClient


def test_search_page_renders(client: TestClient) -> None:
    r = client.get("/search")
    assert r.status_code == 200
    html = r.text
    assert "Find your next experience" in html
    assert 'id="sr-form"' in html
    assert 'id="sr-results"' in html
    assert 'id="sr-pager"' in html


def test_search_page_has_all_fields(client: TestClient) -> None:
    r = client.get("/search")
    html = r.text
    for fid in ["sr-ci", "sr-co", "sr-g", "sr-cat", "sr-sort"]:
        assert f'id="{fid}"' in html


def test_search_page_calls_api(client: TestClient) -> None:
    r = client.get("/search")
    assert "/api/search" in r.text


def test_home_has_new_search_form(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert 'action="/search"' in html
    assert 'name="check_in"' in html
    assert 'name="check_out"' in html
    assert 'name="guests"' in html
