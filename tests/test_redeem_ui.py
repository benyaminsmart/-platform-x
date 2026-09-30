"""Tests for redeem page UI (Phase 44, Step 2)."""
from fastapi.testclient import TestClient


def test_redeem_page_renders(client: TestClient) -> None:
    r = client.get("/account/redeem")
    assert r.status_code == 200
    html = r.text
    assert "Redeem your points" in html
    assert 'id="rd-list"' in html
    assert 'id="rd-balance"' in html
    assert "/rewards/redeem-options" in html
    assert "/rewards/me" in html
