"""Shared Jinja2 template environment + globals."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent

RESERVED_PREFIXES = {
    "docs", "redoc", "openapi.json", "static", "health",
    "auth", "tenants", "services", "bookings", "orders",
    "payments", "rewards", "referrals", "notifications",
    "analytics", "platform", "businesses", "about", "contact", "login", "register",
    "hotels", "restaurants", "travel", "entertainment", "partners",
    "favicon.ico",
}

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _tenant_path(request: Request, suffix: str = "") -> str:
    """Build a path scoped to the current tenant slug in the URL (if present)."""
    parts = [p for p in request.url.path.split("/") if p]
    tenant_slug = parts[0] if parts and parts[0] not in RESERVED_PREFIXES else None
    base = f"/{tenant_slug}" if tenant_slug else ""
    suffix = suffix.lstrip("/")
    if suffix:
        return f"{base}/{suffix}"
    return base or "/"


templates.env.globals["now_year"] = datetime.now(timezone.utc).year
templates.env.globals["tenant_path"] = _tenant_path
