"""Tests for Budget Optimizer UI (Phase 50, Step 3)."""
from fastapi.testclient import TestClient


def test_account_ai_has_budget_button(client: TestClient) -> None:
    r = client.get("/account/ai")
    assert r.status_code == 200
    body = r.text
    assert 'id="open-budget"' in body
    assert 'id="budget-panel"' in body


def test_account_ai_has_budget_inputs(client: TestClient) -> None:
    r = client.get("/account/ai")
    body = r.text
    assert 'id="bud-city"' in body
    assert 'id="bud-days"' in body
    assert 'id="bud-guests"' in body
    assert 'id="bud-budget"' in body
    assert 'id="bud-currency"' in body


def test_account_ai_calls_budget_endpoint(client: TestClient) -> None:
    r = client.get("/account/ai")
    body = r.text
    assert "/api/budget-optimize" in body
    assert 'id="bud-advice"' in body
    assert 'id="bud-package"' in body
    assert 'id="close-budget"' in body
