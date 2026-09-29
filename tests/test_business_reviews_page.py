"""Tests for Business Reviews page (Phase 28, Step 4)."""

from fastapi.testclient import TestClient


def test_reviews_page_renders(client: TestClient) -> None:
    r = client.get("/business/reviews")
    assert r.status_code == 200
    html = r.text
    assert "Guest Reviews" in html
    assert 'class="rv-kpis"' in html
    assert 'id="rv-total"' in html
    assert 'id="rv-avg"' in html
    assert 'id="rv-verified"' in html
    assert 'id="rv-sentiment"' in html


def test_reviews_page_list_and_filters(client: TestClient) -> None:
    r = client.get("/business/reviews")
    html = r.text
    assert 'id="rv-list"' in html
    assert 'id="rv-include-hidden"' in html
    assert 'id="rv-refresh"' in html


def test_reviews_page_modal(client: TestClient) -> None:
    r = client.get("/business/reviews")
    html = r.text
    assert 'id="rv-modal"' in html
    assert 'id="rv-ai-preview"' in html
    assert 'id="rv-response"' in html
    assert 'id="rv-save"' in html
    assert 'id="rv-lang"' in html
    assert 'id="rv-tone"' in html


def test_reviews_page_sidebar_link(client: TestClient) -> None:
    r = client.get("/business/reviews")
    html = r.text
    assert 'href="/business/reviews"' in html
    assert "Reviews" in html
    assert "is-active" in html


def test_reviews_page_uses_correct_apis(client: TestClient) -> None:
    r = client.get("/business/reviews")
    html = r.text
    assert "/business/api/reviews/summary" in html
    assert "/business/api/reviews" in html
    assert "/respond/preview" in html
    assert "/respond" in html
    assert "/hide" in html
    assert "/business/api/me" in html


def test_reviews_page_dark_theme(client: TestClient) -> None:
    r = client.get("/business/reviews")
    html = r.text
    assert "var(--adm-" in html
    assert "#faf8f5" not in html
