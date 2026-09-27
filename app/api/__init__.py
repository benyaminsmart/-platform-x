"""API routers for Platform-X."""

from app.api import auth, bookings, deps, orders, payments, services, tenants

__all__ = ["auth", "bookings", "deps", "orders", "payments", "services", "tenants"]
