"""Tests for the Business Pricing page rendering (Phase 22, Step 5)."""

from fastapi.testclient import TestClient


def test_business_pricing_page_renders(client: TestClient) -> None:
    r = client.get("/business/pricing")
    assert r.status_code == 200
    html = r.text
    assert "Pricing Rules" in html
    assert "Create a new rule" in html
    assert 'id="new-rule-form"' in html
    assert 'id="rules-list"' in html
    assert 'id="r-name"' in html
    assert 'id="r-type"' in html
    assert 'id="r-action-type"' in html
    assert 'id="r-action-value"' in html
    assert 'id="r-priority"' in html
    assert 'id="refresh-rules"' in html


def test_business_pricing_page_sidebar_marks_active(client: TestClient) -> None:
    r = client.get("/business/pricing")
    html = r.text
    assert 'href="/business/pricing"' in html
    # The pricing nav item should have is-active class when on this page
    assert "is-active" in html


def test_business_pricing_page_uses_adm_tokens(client: TestClient) -> None:
    r = client.get("/business/pricing")
    html = r.text
    # No hardcoded light colors
    assert "#faf8f5" not in html
    assert "background: white" not in html
    # Uses dark admin tokens
    assert "var(--adm-" in html


def test_business_pricing_page_api_endpoints_referenced(client: TestClient) -> None:
    r = client.get("/business/pricing")
    html = r.text
    assert "/business/api/pricing/rules" in html
    assert "/business/api/me" in html
