"""Tests for Business Analytics page (Phase 66, Step 3)."""
from fastapi.testclient import TestClient


def test_analytics_page_renders_title(client: TestClient) -> None:
    r = client.get("/business/analytics")
    assert r.status_code == 200
    assert "Analytics" in r.text


def test_analytics_page_uses_adm_tokens(client: TestClient) -> None:
    r = client.get("/business/analytics")
    body = r.text
    assert "--adm-" in body


def test_analytics_page_has_kpi_hooks(client: TestClient) -> None:
    r = client.get("/business/analytics")
    body = r.text
    assert 'id="an-kpis"' in body
    assert 'id="an-forecast"' in body
    assert 'id="an-nearfull"' in body
    assert 'id="an-capacity"' in body
    assert 'id="an-refresh"' in body


def test_analytics_page_calls_insights_api(client: TestClient) -> None:
    r = client.get("/business/analytics")
    body = r.text
    assert "/business/api/insights/occupancy" in body
    assert "/business/api/insights/revenue/forecast" in body
    assert "/business/api/insights/capacity/available" in body
