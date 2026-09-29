"""Tests for the Business Marketing Copilot page (Phase 25, Step 5)."""

from fastapi.testclient import TestClient


def test_marketing_page_renders(client: TestClient) -> None:
    r = client.get("/business/marketing")
    assert r.status_code == 200
    html = r.text
    assert "Marketing Copilot" in html
    assert 'id="mk-segs"' in html
    assert 'id="mk-sug-btn"' in html
    assert 'id="mk-gen-btn"' in html
    assert 'id="mk-disc-btn"' in html
    assert 'id="mk-send-btn"' in html
    assert 'id="mk-alert"' in html


def test_marketing_page_has_all_segments_in_send_dropdown(client: TestClient) -> None:
    r = client.get("/business/marketing")
    html = r.text
    for seg in ["past_bookers", "inactive_90d", "high_value", "new_30d", "loyalty_gold_plus", "all"]:
        assert f'value="{seg}"' in html


def test_marketing_page_sidebar_link(client: TestClient) -> None:
    r = client.get("/business/marketing")
    html = r.text
    assert 'href="/business/marketing"' in html
    assert "Marketing" in html
    assert "is-active" in html


def test_marketing_page_uses_correct_apis(client: TestClient) -> None:
    r = client.get("/business/marketing")
    html = r.text
    assert "/business/api/marketing/config" in html
    assert "/business/api/marketing/segments" in html
    assert "/business/api/marketing/campaigns/suggest" in html
    assert "/business/api/marketing/campaigns/generate" in html
    assert "/business/api/marketing/campaigns/send" in html
    assert "/business/api/marketing/discounts/suggest" in html
    assert "/business/api/me" in html


def test_marketing_page_dark_theme(client: TestClient) -> None:
    r = client.get("/business/marketing")
    html = r.text
    assert "var(--adm-" in html
    assert "#faf8f5" not in html


def test_marketing_page_shows_max_discount_cap(client: TestClient) -> None:
    r = client.get("/business/marketing")
    html = r.text
    # The max cap should be rendered from the server (20.0)
    assert "20.0%" in html
