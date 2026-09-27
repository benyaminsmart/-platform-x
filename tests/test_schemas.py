"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas import RegisterRequest


def _valid_kwargs(**overrides):
    base = dict(
        email="user@example.com",
        password="Pass1234",
        first_name="Ali",
        last_name="Karimi",
    )
    base.update(overrides)
    return base


def test_valid_register() -> None:
    r = RegisterRequest(**_valid_kwargs())
    assert r.email == "user@example.com"
    assert r.language == "en"
    assert r.preferred_currency == "AED"
    assert r.phone is None


def test_reject_short_password() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(**_valid_kwargs(password="Ab1"))


def test_reject_password_without_digit() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(**_valid_kwargs(password="allletters"))


def test_reject_password_without_letter() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(**_valid_kwargs(password="12345678"))


def test_reject_invalid_email() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(**_valid_kwargs(email="not-an-email"))


def test_reject_empty_first_name() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(**_valid_kwargs(first_name=""))


def test_phone_optional() -> None:
    r = RegisterRequest(**_valid_kwargs(phone="+971500000000"))
    assert r.phone == "+971500000000"
