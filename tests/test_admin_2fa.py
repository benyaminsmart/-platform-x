"""Tests for platform admin 2FA (TOTP) flow."""
from __future__ import annotations

import pyotp
import pytest

from app.core.security import hash_password
from app.models.platform_admin import PlatformAdmin


@pytest.fixture
def admin_user(db):
    """Create a fresh platform admin for 2FA tests."""
    admin = PlatformAdmin(
        email="admin-2fa-test@example.com",
        password_hash=hash_password("secret-password-123"),
        name="2FA Test Admin",
        role="admin",
        mfa_enabled=False,
        mfa_secret=None,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def _login(client, email: str, password: str):
    return client.post(
        "/platform/auth/login",
        json={"email": email, "password": password},
    )


def test_login_without_2fa_returns_full_token(client, admin_user):
    r = _login(client, admin_user.email, "secret-password-123")
    assert r.status_code == 200
    data = r.json()
    assert data["mfa_required"] is False
    assert data["access_token"]
    assert data["expires_in"] > 0


def test_login_with_wrong_password_returns_401(client, admin_user):
    r = _login(client, admin_user.email, "wrong-password")
    assert r.status_code == 401


def test_2fa_setup_requires_auth(client):
    r = client.post("/platform/auth/2fa/setup")
    assert r.status_code in (401, 403)


def test_2fa_full_flow_enable_and_login(client, admin_user):
    # 1) Login (no 2FA yet) -> full token
    r = _login(client, admin_user.email, "secret-password-123")
    assert r.status_code == 200
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # 2) Setup: get secret
    r = client.post("/platform/auth/2fa/setup", headers=auth)
    assert r.status_code == 200
    secret = r.json()["secret"]
    assert secret

    # 3) Verify: enable with current TOTP
    code = pyotp.TOTP(secret).now()
    r = client.post(
        "/platform/auth/2fa/verify",
        json={"totp_code": code},
        headers=auth,
    )
    assert r.status_code == 200
    assert "enabled" in r.json()["message"].lower()

    # 4) Login again -> should now return mfa_required with mfa_token
    r = _login(client, admin_user.email, "secret-password-123")
    assert r.status_code == 200
    data = r.json()
    assert data["mfa_required"] is True
    assert data["mfa_token"]
    mfa_token = data["mfa_token"]

    # 5) Complete 2FA login with TOTP
    code = pyotp.TOTP(secret).now()
    r = client.post(
        "/platform/auth/2fa/login",
        json={"mfa_token": mfa_token, "totp_code": code},
    )
    assert r.status_code == 200
    final = r.json()
    assert final["access_token"]
    assert final["expires_in"] > 0


def test_2fa_login_with_wrong_code_returns_401(client, admin_user):
    # Setup + enable
    r = _login(client, admin_user.email, "secret-password-123")
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    secret = client.post("/platform/auth/2fa/setup", headers=auth).json()["secret"]
    pyotp_now = pyotp.TOTP(secret).now()
    client.post(
        "/platform/auth/2fa/verify",
        json={"totp_code": pyotp_now},
        headers=auth,
    )

    # Login -> mfa_token
    r = _login(client, admin_user.email, "secret-password-123")
    mfa_token = r.json()["mfa_token"]

    # Wrong code
    r = client.post(
        "/platform/auth/2fa/login",
        json={"mfa_token": mfa_token, "totp_code": "000000"},
    )
    assert r.status_code == 401


def test_2fa_login_with_access_token_rejected(client, admin_user):
    """An access token must not work where an mfa_token is required."""
    r = _login(client, admin_user.email, "secret-password-123")
    access_token = r.json()["access_token"]
    r = client.post(
        "/platform/auth/2fa/login",
        json={"mfa_token": access_token, "totp_code": "000000"},
    )
    assert r.status_code == 401


def test_2fa_disable_requires_valid_code(client, admin_user):
    # Setup + enable
    r = _login(client, admin_user.email, "secret-password-123")
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    secret = client.post("/platform/auth/2fa/setup", headers=auth).json()["secret"]
    client.post(
        "/platform/auth/2fa/verify",
        json={"totp_code": pyotp.TOTP(secret).now()},
        headers=auth,
    )

    # Disable with wrong code
    r = client.post(
        "/platform/auth/2fa/disable",
        json={"totp_code": "000000"},
        headers=auth,
    )
    assert r.status_code == 400

    # Disable with correct code
    r = client.post(
        "/platform/auth/2fa/disable",
        json={"totp_code": pyotp.TOTP(secret).now()},
        headers=auth,
    )
    assert r.status_code == 200
    assert "disabled" in r.json()["message"].lower()


def test_2fa_verify_without_setup_returns_400(client, admin_user):
    r = _login(client, admin_user.email, "secret-password-123")
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/platform/auth/2fa/verify",
        json={"totp_code": "000000"},
        headers=auth,
    )
    assert r.status_code == 400
