"""Tests for Business Insights page (Phase 26, Step 6)."""

from fastapi.testclient import TestClient


def test_insights_page_renders(client: TestClient) -> None:
    r = client.get("/business/insights")
    assert r.status_code == 200
    html = r.text
    assert "Business Insights" in html
    assert 'class="in-kpis"' in html
    assert 'id="kpi-occ"' in html
    assert 'id="kpi-nights"' in html
    assert 'id="kpi-rev"' in html
    assert 'id="kpi-fc"' in html


def test_insights_page_heatmap_containers(client: TestClient) -> None:
    r = client.get("/business/insights")
    html = r.text
    assert 'id="hm-dow"' in html
    assert 'id="hm-cal"' in html
    assert 'id="hm-days"' in html


def test_insights_page_capacity_and_forecast(client: TestClient) -> None:
    r = client.get("/business/insights")
    html = r.text
    assert 'id="cap-summary"' in html
    assert 'id="cap-near-full"' in html
    assert 'id="cap-refresh"' in html
    assert 'id="fc-btn"' in html
    assert 'id="fc-out"' in html


def test_insights_page_sidebar_link(client: TestClient) -> None:
    r = client.get("/business/insights")
    html = r.text
    assert 'href="/business/insights"' in html
    assert "Insights" in html
    assert "is-active" in html


def test_insights_page_uses_correct_apis(client: TestClient) -> None:
    r = client.get("/business/insights")
    html = r.text
    assert "/business/api/insights/occupancy" in html
    assert "/business/api/insights/occupancy/trend" in html
    assert "/business/api/insights/heatmap/day-of-week" in html
    assert "/business/api/insights/heatmap/calendar" in html
    assert "/business/api/insights/capacity/available" in html
    assert "/business/api/insights/capacity/near-full" in html
    assert "/business/api/insights/revenue/forecast" in html
    assert "/business/api/me" in html


def test_insights_page_dark_theme(client: TestClient) -> None:
    r = client.get("/business/insights")
    html = r.text
    assert "var(--adm-" in html
    assert "#faf8f5" not in html
