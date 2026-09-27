"""API routers for Platform-X."""

from app.api import (
    auth,
    bookings,
    deps,
    notifications,
    orders,
    payments,
    referrals,
    rewards,
    services,
    tenants,
)

__all__ = [
    "auth",
    "bookings",
    "deps",
    "notifications",
    "orders",
    "payments",
    "referrals",
    "rewards",
    "services",
    "tenants",
]
