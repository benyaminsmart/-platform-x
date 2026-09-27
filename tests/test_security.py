"""Tests for security primitives."""

from datetime import timedelta

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_returns_bcrypt_hash() -> None:
    h = hash_password("Test123!")
    assert h.startswith("$2")
    assert len(h) == 60


def test_hash_password_is_salted() -> None:
    assert hash_password("same") != hash_password("same")


def test_verify_password_correct() -> None:
    h = hash_password("secret")
    assert verify_password("secret", h) is True


def test_verify_password_wrong() -> None:
    h = hash_password("secret")
    assert verify_password("wrong", h) is False


def test_verify_password_invalid_hash_returns_false() -> None:
    assert verify_password("any", "not-a-hash") is False


def test_long_password_truncated_to_bcrypt_limit() -> None:
    long_a = "a" * 100
    long_b = "a" * 72 + "b" * 28
    h = hash_password(long_a)
    # bcrypt only sees first 72 bytes → both should match
    assert verify_password(long_b, h) is True


def test_create_and_decode_token() -> None:
    token = create_access_token("user-1", tenant_id="t-1")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "t-1"
    assert "exp" in payload and "iat" in payload


def test_token_extra_claims() -> None:
    token = create_access_token("u", extra_claims={"role": "admin"})
    payload = decode_access_token(token)
    assert payload["role"] == "admin"


def test_token_expired_raises() -> None:
    token = create_access_token("u", expires_delta=timedelta(seconds=-1))
    with pytest.raises(JWTError):
        decode_access_token(token)


def test_token_tampered_raises() -> None:
    token = create_access_token("u")
    with pytest.raises(JWTError):
        decode_access_token(token + "x")
