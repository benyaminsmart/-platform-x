"""Tests for no-show UI in dashboard (Phase 35, Step 5)."""
from fastapi.testclient import TestClient


def test_dashboard_has_no_show_card(client: TestClient) -> None:
    r = client.get("/business/dashboard")
    assert r.status_code == 200
    html = r.text
    assert "No-shows" in html
    assert 'id="ns-list"' in html
    assert 'id="ns-refresh"' in html
    assert "/business/api/no-shows" in html
