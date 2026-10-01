"""Tests for AI Receptionist UI on /business/messages (Phase 53, Step 3)."""
from fastapi.testclient import TestClient


def test_messages_page_has_ai_draft_button(client: TestClient) -> None:
    r = client.get("/business/messages")
    assert r.status_code == 200
    body = r.text
    assert 'id="msg-ai-draft"' in body
    assert "AI Draft" in body


def test_messages_page_calls_draft_endpoint(client: TestClient) -> None:
    r = client.get("/business/messages")
    body = r.text
    assert "/draft" in body
    assert "Drafting…" in body
