"""Tests for the Business Content Studio page (Phase 23, Step 4)."""

from fastapi.testclient import TestClient


def test_content_page_renders(client: TestClient) -> None:
    r = client.get("/business/content")
    assert r.status_code == 200
    html = r.text
    assert "Content Studio" in html
    assert 'id="tg-btn"' in html
    assert 'id="tg-lang"' in html
    assert 'id="tg-result"' in html


def test_content_page_import_panel(client: TestClient) -> None:
    r = client.get("/business/content")
    html = r.text
    assert 'id="imp-toggle"' in html
    assert 'id="imp-panel"' in html
    assert 'id="imp-text"' in html
    assert 'id="imp-type"' in html
    assert 'id="imp-lang"' in html
    assert 'id="imp-parse"' in html
    assert 'id="imp-create"' in html
    assert 'id="imp-result"' in html


def test_content_page_service_list(client: TestClient) -> None:
    r = client.get("/business/content")
    html = r.text
    assert 'id="svc-list"' in html
    assert 'id="svc-refresh"' in html


def test_content_page_sidebar_link_active(client: TestClient) -> None:
    r = client.get("/business/content")
    html = r.text
    assert 'href="/business/content"' in html
    assert "Content Studio" in html
    assert "is-active" in html


def test_content_page_uses_correct_apis(client: TestClient) -> None:
    r = client.get("/business/content")
    html = r.text
    assert "/business/api/ai/content/tagline" in html
    assert "/business/api/ai/content/import/preview" in html
    assert "/business/api/ai/content/import/create" in html
    assert "/business/api/ai/content/service/" in html
    assert "/business/api/services" in html
    assert "/business/api/me" in html


def test_content_page_dark_theme(client: TestClient) -> None:
    r = client.get("/business/content")
    html = r.text
    assert "var(--adm-" in html
    assert "#faf8f5" not in html
