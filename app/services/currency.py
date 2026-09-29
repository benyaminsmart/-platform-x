"""Currency conversion — fixed exchange rates.

Design (Wave 0):
- Base currency: AED (all prices stored in AED).
- Fixed rates in code; updated manually when needed.
- Rates are approximate and marked as such in the UI.
- Not for financial settlement — display only.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


BASE_CURRENCY = "AED"

# 1 unit of foreign currency = X AED
# Example: 1 USD = 3.67 AED
RATES_TO_AED: dict[str, Decimal] = {
    "AED": Decimal("1"),
    "USD": Decimal("3.67"),
    "EUR": Decimal("4.00"),
    "GBP": Decimal("4.65"),
    "SAR": Decimal("0.98"),
}

SUPPORTED_CURRENCIES = tuple(RATES_TO_AED.keys())


def _round2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def is_supported(code: str) -> bool:
    return (code or "").upper() in RATES_TO_AED


def convert_from_aed(amount: float | Decimal | str, to_currency: str) -> Decimal:
    """Convert AED amount to target currency."""
    code = (to_currency or BASE_CURRENCY).upper()
    if code not in RATES_TO_AED:
        raise ValueError(f"unsupported currency: {code}")
    rate = RATES_TO_AED[code]  # 1 unit foreign = rate AED
    aed = Decimal(str(amount))
    if rate == 0:
        return Decimal("0.00")
    return _round2(aed / rate)


def convert_to_aed(amount: float | Decimal | str, from_currency: str) -> Decimal:
    code = (from_currency or BASE_CURRENCY).upper()
    if code not in RATES_TO_AED:
        raise ValueError(f"unsupported currency: {code}")
    rate = RATES_TO_AED[code]
    return _round2(Decimal(str(amount)) * rate)


def get_rates_snapshot() -> dict[str, Any]:
    """Return rates for display."""
    return {
        "base": BASE_CURRENCY,
        "supported": list(SUPPORTED_CURRENCIES),
        "rates_to_aed": {k: str(v) for k, v in RATES_TO_AED.items()},
        "note": "Approximate display rates. Not for financial settlement.",
    }
