"""Tests for production hardening rules in Settings."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _base_prod():
    return dict(
        APP_ENV="production",
        APP_DEBUG=False,
        SECRET_KEY="x" * 40,
        CORS_ORIGINS=["https://platform-x.example"],
        ENABLE_MOCK_PAYMENTS=False,
    )


def test_production_valid_config() -> None:
    s = Settings(**_base_prod())
    assert s.APP_ENV == "production"


def test_production_rejects_dev_secret() -> None:
    cfg = _base_prod()
    cfg["SECRET_KEY"] = "dev-secret-key-change-in-production"
    with pytest.raises(ValidationError):
        Settings(**cfg)


def test_production_rejects_short_secret() -> None:
    cfg = _base_prod()
    cfg["SECRET_KEY"] = "short"
    with pytest.raises(ValidationError):
        Settings(**cfg)


def test_production_rejects_debug() -> None:
    cfg = _base_prod()
    cfg["APP_DEBUG"] = True
    with pytest.raises(ValidationError):
        Settings(**cfg)


def test_production_rejects_mock_payments() -> None:
    cfg = _base_prod()
    cfg["ENABLE_MOCK_PAYMENTS"] = True
    with pytest.raises(ValidationError):
        Settings(**cfg)


def test_production_rejects_localhost_cors() -> None:
    cfg = _base_prod()
    cfg["CORS_ORIGINS"] = ["http://localhost:8000"]
    with pytest.raises(ValidationError):
        Settings(**cfg)


def test_development_allows_defaults() -> None:
    s = Settings(APP_ENV="development")
    assert s.APP_DEBUG is True
    assert s.ENABLE_MOCK_PAYMENTS is True
