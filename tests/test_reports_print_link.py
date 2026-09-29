"""Test: print report button in dashboard (Phase 34, Step 4)."""
from fastapi.testclient import TestClient


def test_dashboard_has_print_report_button(client: TestClient) -> None:
    r = client.get("/business/dashboard")
    assert r.status_code == 200
    html = r.text
    assert "exp-print-report" in html
    assert "/business/reports/print" in html
