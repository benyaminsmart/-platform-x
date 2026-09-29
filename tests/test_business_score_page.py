"""Tests for the Business /business/score page (Phase 29, Step 7)."""

from fastapi.testclient import TestClient


def test_business_score_page_renders(client: TestClient) -> None:
    r = client.get("/business/score")
    assert r.status_code == 200
    html = r.text
    assert "My Leaderboard Score" in html
    assert 'id="score-block"' in html
    assert 'id="score-empty"' in html
    assert 'id="sc-overall"' in html
    assert 'id="sc-criteria-list"' in html
    assert 'id="btn-tips"' in html
    assert 'id="sc-tips"' in html


def test_business_score_page_sidebar_link(client: TestClient) -> None:
    r = client.get("/business/score")
    html = r.text
    assert 'href="/business/score"' in html
    assert "My Score" in html


def test_business_score_page_uses_correct_apis(client: TestClient) -> None:
    r = client.get("/business/score")
    html = r.text
    assert "/business/api/score" in html
    assert "/business/api/score/tips" in html
    assert "/business/api/me" in html


def test_business_score_page_uses_adm_tokens(client: TestClient) -> None:
    r = client.get("/business/score")
    html = r.text
    assert "var(--adm-" in html
    # no hardcoded light theme (except pure-white on colored badges which is fine)
    assert "#faf8f5" not in html
