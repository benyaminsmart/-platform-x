"""Tests for expanded /docs/api page (Phase 62, Step 1)."""
from fastapi.testclient import TestClient


def test_api_docs_page_renders(client: TestClient) -> None:
    r = client.get("/docs/api")
    assert r.status_code == 200
    body = r.text
    assert "Platform-X API" in body
    assert "Public API" in body


def test_api_docs_has_all_sections(client: TestClient) -> None:
    r = client.get("/docs/api")
    body = r.text
    for anchor in [
        'id="public"', 'id="auth"', 'id="guest"', 'id="booking"',
        'id="rewards"', 'id="extras"', 'id="discovery"',
        'id="ai-public"', 'id="business"', 'id="business-ai"',
        'id="webhooks"', 'id="errors"',
    ]:
        assert anchor in body, f"missing section {anchor}"


def test_api_docs_covers_new_phases(client: TestClient) -> None:
    """Docs must mention features built in Phases 45-60."""
    r = client.get("/docs/api")
    body = r.text
    for feature in [
        "price-locks", "waitlist", "installment", "trust-score",
        "budget-optimize", "bundle-deals", "auto-repricing",
        "peer-benchmark", "upsell",
    ]:
        assert feature in body, f"missing feature: {feature}"
