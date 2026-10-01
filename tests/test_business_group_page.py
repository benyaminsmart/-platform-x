"""Tests for Business Group dashboard page (Phase 58, Step 3)."""
from fastapi.testclient import TestClient


def test_page_renders_title(client: TestClient) -> None:
    r = client.get("/business/group")
    assert r.status_code == 200
    body = r.text
    assert "Group Dashboard" in body


def test_page_has_ui_hooks(client: TestClient) -> None:
    """The content block is omitted when unauth. Assert on the JS hooks
    which are always rendered in the script block."""
    r = client.get("/business/group")
    body = r.text
    assert "bg-list" in body
    assert "bg-name" in body
    assert "bg-create" in body
    assert "bg-detail-card" in body
    assert "bg-attach" in body


def test_page_calls_api(client: TestClient) -> None:
    r = client.get("/business/group")
    body = r.text
    assert "/business/api/groups" in body


def test_sidebar_link_present(client: TestClient) -> None:
    r = client.get("/business/dashboard")
    assert r.status_code == 200
    body = r.text
    assert "/business/group" in body
