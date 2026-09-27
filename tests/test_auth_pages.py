"""Tests for auth HTML pages."""

from fastapi.testclient import TestClient


def test_login_page(client: TestClient) -> None:
    resp = client.get("/login")
    assert resp.status_code == 200
    assert 'id="login-form"' in resp.text
    assert "Sign in" in resp.text


def test_register_page(client: TestClient) -> None:
    resp = client.get("/register")
    assert resp.status_code == 200
    assert 'id="register-form"' in resp.text
    assert "Create account" in resp.text


def test_login_page_has_api_script(client: TestClient) -> None:
    resp = client.get("/login")
    assert '/static/js/auth.js' in resp.text
    assert 'PX.initLogin()' in resp.text


def test_register_page_has_api_script(client: TestClient) -> None:
    resp = client.get("/register")
    assert '/static/js/auth.js' in resp.text
    assert 'PX.initRegister()' in resp.text


def test_header_uses_web_auth_paths(client: TestClient) -> None:
    """Header must link to /login and /register (not /auth/* which are API)."""
    resp = client.get("/")
    assert 'href="/login"' in resp.text
    assert 'href="/register"' in resp.text


def test_auth_js_served(client: TestClient) -> None:
    resp = client.get("/static/js/auth.js")
    assert resp.status_code == 200
    assert "PX.initLogin" in resp.text
    assert "PX.initRegister" in resp.text


def test_login_and_register_not_tenant_slug(client: TestClient) -> None:
    """GET /login/ shouldn't be a tenant lookup."""
    resp = client.get("/login/")
    assert resp.status_code == 404
