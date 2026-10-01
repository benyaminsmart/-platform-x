"""Tests for AI Voice Booking UI (Phase 64, Step 3)."""
from fastapi.testclient import TestClient


def test_account_ai_has_voice_button(client: TestClient) -> None:
    r = client.get("/account/ai")
    assert r.status_code == 200
    body = r.text
    assert 'id="open-voice"' in body
    assert 'id="voice-panel"' in body


def test_account_ai_has_voice_inputs(client: TestClient) -> None:
    r = client.get("/account/ai")
    body = r.text
    assert 'id="voice-transcript"' in body
    assert 'id="voice-run"' in body
    assert 'id="voice-intent"' in body
    assert 'id="voice-reply"' in body
    assert 'id="voice-matches"' in body
    assert 'id="close-voice"' in body


def test_account_ai_calls_voice_endpoint(client: TestClient) -> None:
    r = client.get("/account/ai")
    body = r.text
    assert "/account/api/ai/voice" in body
    assert "Parsed intent" in body
