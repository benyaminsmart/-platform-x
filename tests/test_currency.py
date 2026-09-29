"""Tests for currency conversion (Phase 30, Step 6)."""
from decimal import Decimal
import pytest
from app.services import currency


def test_base_currency_is_aed():
    assert currency.BASE_CURRENCY == "AED"
    assert "AED" in currency.SUPPORTED_CURRENCIES
    assert "USD" in currency.SUPPORTED_CURRENCIES


def test_is_supported():
    assert currency.is_supported("USD")
    assert currency.is_supported("usd")
    assert not currency.is_supported("XYZ")
    assert not currency.is_supported("")


def test_convert_aed_to_usd():
    # 367 AED / 3.67 = 100 USD
    r = currency.convert_from_aed(367, "USD")
    assert r == Decimal("100.00")


def test_convert_aed_to_eur():
    # 400 AED / 4.00 = 100 EUR
    r = currency.convert_from_aed(400, "EUR")
    assert r == Decimal("100.00")


def test_convert_aed_to_aed_noop():
    r = currency.convert_from_aed(500, "AED")
    assert r == Decimal("500.00")


def test_convert_to_aed():
    r = currency.convert_to_aed(100, "USD")
    assert r == Decimal("367.00")


def test_unsupported_raises():
    with pytest.raises(ValueError):
        currency.convert_from_aed(100, "XYZ")
    with pytest.raises(ValueError):
        currency.convert_to_aed(100, "XYZ")


def test_rounding():
    r = currency.convert_from_aed(100, "USD")
    # 100 / 3.67 = 27.2479... -> 27.25
    assert r == Decimal("27.25")


def test_rates_snapshot():
    s = currency.get_rates_snapshot()
    assert s["base"] == "AED"
    assert "AED" in s["supported"]
    assert s["rates_to_aed"]["USD"] == "3.67"
    assert "note" in s
