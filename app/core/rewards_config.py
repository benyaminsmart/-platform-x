"""Rewards engine configuration constants.

Phase 75 (Stage 2, plan §6-§8, §11, §18).

Values are kept here as the code-level fallback; the authoritative
DB-stored values live in RewardRule (per category). The seed script
uses these to populate the DB.
"""

from __future__ import annotations

from decimal import Decimal


# --- Category reward targets (plan §6) ---
CATEGORY_RATES: dict[str, dict[str, Decimal]] = {
    "HOTEL": {
        "platform_reward_rate": Decimal("0.0100"),
        "max_reward_amount": Decimal("200.00"),
        "min_transaction_amount": Decimal("100.00"),
    },
    "FLIGHT": {
        "platform_reward_rate": Decimal("0.0050"),
        "max_reward_amount": Decimal("150.00"),
        "min_transaction_amount": Decimal("200.00"),
    },
    "EXPERIENCE": {
        "platform_reward_rate": Decimal("0.0150"),
        "max_reward_amount": Decimal("100.00"),
        "min_transaction_amount": Decimal("50.00"),
    },
    "DINING": {
        "platform_reward_rate": Decimal("0.0120"),
        "max_reward_amount": Decimal("60.00"),
        "min_transaction_amount": Decimal("40.00"),
    },
}

# --- User tiers (plan §8) ---
TIERS: list[dict] = [
    {"name": "EXPLORER", "min_transactions": 0,  "max_transactions": 2,    "multiplier": Decimal("1.00")},
    {"name": "TRAVELER", "min_transactions": 3,  "max_transactions": 5,    "multiplier": Decimal("1.25")},
    {"name": "INSIDER",  "min_transactions": 6,  "max_transactions": 9,    "multiplier": Decimal("1.50")},
    {"name": "VIP",      "min_transactions": 10, "max_transactions": None, "multiplier": Decimal("2.00")},
]

DEFAULT_TIER = "EXPLORER"

# --- Migration mapping (old → new) ---
LEGACY_TIER_MAP: dict[str, str] = {
    "welcome": "EXPLORER",
    "silver": "TRAVELER",
    "gold": "INSIDER",
    "platinum": "VIP",
    "royal": "VIP",
}

# --- Referral (plan §10-§11) ---
REFERRAL_REFERRER_CREDIT = Decimal("20.00")
REFERRAL_REFERRED_CREDIT = Decimal("15.00")
REFERRAL_MIN_QUALIFYING_AMOUNT = Decimal("300.00")
REFERRAL_MAX_CREDIT_PER_USER_MONTH = Decimal("100.00")

# --- Referral fraud thresholds (plan §12) ---
REFERRAL_VELOCITY_MAX_PER_24H = 5
REFERRAL_MAX_CANCELLATION_RATE = 0.50
REFERRAL_MIN_BOOKINGS_FOR_RATE = 4
REFERRAL_MIN_ACCOUNT_AGE_HOURS = 24
REFERRAL_FRAUD_REVIEW_THRESHOLD = 30

# --- Expiration windows (plan §14) ---
EXPIRATION_WINDOWS_DAYS = (30, 60, 90)
EXPIRATION_DEFAULT_DAYS = 60
EXPIRATION_NOTIFY_DAYS_BEFORE = (7, 3, 1)

# --- Economics (plan §18) ---
DEFAULT_PLATFORM_COMMISSION_RATE = Decimal("0.06")  # 6%
DEFAULT_REWARD_COST_BUDGET_PCT = Decimal("0.50")    # max reward cost = 50% of commission


def tier_for_transactions(n: int) -> str:
    """Return the tier name for a qualifying-transaction count."""
    for t in TIERS:
        upper = t["max_transactions"]
        if n >= t["min_transactions"] and (upper is None or n <= upper):
            return t["name"]
    return DEFAULT_TIER


def multiplier_for_tier(tier: str) -> Decimal:
    """Return the multiplier for a tier name (default 1.00)."""
    for t in TIERS:
        if t["name"] == tier:
            return t["multiplier"]
    return Decimal("1.00")
