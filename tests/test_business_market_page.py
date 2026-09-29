"""Tests for Business Market Insights page (Phase 27, Step 4)."""

from fastapi.testclient import TestClient


def test_market_page_renders(client: TestClient) -> None:
    r = client.get("/business/market")
    assert r.status_code == 200
    html = r.text
    assert "Market Insights" in html
    assert 'id="mk-cohort"' in html
    assert 'id="mk-refresh"' in html


def test_market_page_position_cards(client: TestClient) -> None:
    r = client.get("/business/market")
    html = r.text
    for k in ("pos-price-val", "pos-rating-val", "pos-svc-val", "pos-bk-val"):
        assert f'id="{k}"' in html
    for k in ("pos-price-bar", "pos-rating-bar", "pos-svc-bar", "pos-bk-bar"):
        assert f'id="{k}"' in html


def test_market_page_strengths_weaknesses(client: TestClient) -> None:
    r = client.get("/business/market")
    html = r.text
    assert 'id="mk-strengths"' in html
    assert 'id="mk-weaknesses"' in html
    assert 'id="mk-bench"' in html


def test_market_page_ai_controls(client: TestClient) -> None:
    r = client.get("/business/market")
    html = r.text
    assert 'id="ai-btn"' in html
    assert 'id="ai-lang"' in html
    assert 'id="mk-ai-out"' in html


def test_market_page_sidebar_link(client: TestClient) -> None:
    r = client.get("/business/market")
    html = r.text
    assert 'href="/business/market"' in html
    assert "Market Insights" in html
    assert "is-active" in html


def test_market_page_uses_correct_apis(client: TestClient) -> None:
    r = client.get("/business/market")
    html = r.text
    assert "/business/api/market/insights" in html
    assert "/business/api/market/insights/ai" in html
    assert "/business/api/me" in html


def test_market_page_dark_theme(client: TestClient) -> None:
    r = client.get("/business/market")
    html = r.text
    assert "var(--adm-" in html
    assert "#faf8f5" not in html
