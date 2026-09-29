"""Tests for business messages page (Phase 39, Step 6)."""
from fastapi.testclient import TestClient


def test_messages_page_renders(client: TestClient) -> None:
    r = client.get("/business/messages")
    assert r.status_code == 200
    html = r.text
    assert "Messages" in html
    assert 'id="msg-threads"' in html
    assert 'id="msg-form"' in html


def test_messages_sidebar_link(client: TestClient) -> None:
    r = client.get("/business/messages")
    assert 'href="/business/messages"' in r.text
    assert "is-active" in r.text


def test_messages_page_apis(client: TestClient) -> None:
    r = client.get("/business/messages")
    html = r.text
    assert "/business/api/messages/threads" in html
    assert "/business/api/me" in html
