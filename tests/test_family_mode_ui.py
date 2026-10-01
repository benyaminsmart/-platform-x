"""Tests for Family & Kids Mode UI on /search (Phase 55, Step 2)."""
from fastapi.testclient import TestClient


def test_search_page_has_family_field(client: TestClient) -> None:
    r = client.get("/search")
    assert r.status_code == 200
    body = r.text
    assert 'id="sr-family"' in body
    assert "Family &amp; Kids" in body or "Family & Kids" in body
    assert "Family-friendly only" in body


def test_search_page_reads_family_param(client: TestClient) -> None:
    r = client.get("/search")
    body = r.text
    assert 'family_friendly: document.getElementById("sr-family").value' in body
    assert 'u.has("family_friendly")' in body


def test_search_page_renders_family_badge(client: TestClient) -> None:
    r = client.get("/search")
    body = r.text
    assert "sr-family" in body
    assert "Family-friendly" in body  # title attribute
