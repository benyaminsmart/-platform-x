"""Tests for the Business AI page rendering (Phase 21, Step 4).

The page itself is client-side (JS-driven), so we only assert:
- HTML renders without error
- key UI elements are present (tabs, coach cards, buttons)
- no tenant slug is hardcoded (regression guard for the previous bug)
"""

from fastapi.testclient import TestClient


def test_business_ai_page_renders(client: TestClient) -> None:
    r = client.get("/business/ai")
    assert r.status_code == 200
    html = r.text
    # Tabs
    assert "Pricing Coach" in html
    assert 'data-tab="chat"' in html
    assert 'data-tab="coach"' in html
    # Coach cards
    assert 'data-act="analyze"' in html
    assert 'data-act="suggest"' in html
    assert 'data-act="forecast"' in html
    assert 'data-act="insights"' in html
    # Forecast days selector
    assert 'id="forecast-days"' in html
    # Output containers
    for act in ("analyze", "suggest", "forecast", "insights"):
        assert f'id="out-{act}"' in html


def test_business_ai_page_no_hardcoded_slug(client: TestClient) -> None:
    """Regression: the old template hardcoded 'trianon-hotel' everywhere."""
    r = client.get("/business/ai")
    html = r.text
    # The word trianon must not appear as a hardcoded tenant
    assert 'X-Tenant-Slug": "trianon-hotel"' not in html
    assert '"trianon-hotel"' not in html
    # Slug must be resolved dynamically via /business/api/me
    assert "/business/api/me" in html


def test_business_ai_page_uses_correct_api_paths(client: TestClient) -> None:
    r = client.get("/business/ai")
    html = r.text
    assert "/business/api/ai/chat" in html
    assert "/business/api/ai/pricing/analyze" in html
    assert "/business/api/ai/pricing/suggest" in html
    assert "/business/api/ai/demand/forecast" in html
    assert "/business/api/ai/insights" in html
