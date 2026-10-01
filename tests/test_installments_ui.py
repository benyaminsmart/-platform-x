"""Tests for Installments UI page (Phase 57, Step 3)."""
from fastapi.testclient import TestClient


def test_installments_page_renders(client: TestClient) -> None:
    r = client.get("/account/installments")
    assert r.status_code == 200
    body = r.text
    assert "Installment Plans" in body
    assert 'id="ins-body"' in body
    assert 'id="ins-refresh"' in body


def test_installments_page_calls_api(client: TestClient) -> None:
    r = client.get("/account/installments")
    body = r.text
    assert "/me/installment-plans" in body
    assert "/me/installment-plans/installments/" in body
