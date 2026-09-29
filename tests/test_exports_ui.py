"""Tests for exports UI in business dashboard (Phase 34, Step 2)."""
from fastapi.testclient import TestClient


def test_dashboard_has_exports_card(client: TestClient) -> None:
    r = client.get("/business/dashboard")
    assert r.status_code == 200
    html = r.text
    assert "Reports &amp; Exports" in html or "Reports & Exports" in html
    assert "exp-days" in html
    assert "/business/api/exports/bookings.csv" in html
    assert "/business/api/exports/customers.csv" in html
    assert "/business/api/exports/revenue.csv" in html
    assert "exp-btn" in html
