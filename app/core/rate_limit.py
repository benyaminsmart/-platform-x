"""Rate limiting configuration for Platform-X."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


# Feature flag: disable rate limiting via env (used in tests)
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() != "false"


def client_key(request: Request) -> str:
    """Return the client identifier for rate limiting.

    Uses the X-Forwarded-For header (set by Cloudflare) when present,
    otherwise falls back to the direct remote address.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=client_key,
    default_limits=[],
    storage_uri="memory://",
    enabled=RATE_LIMIT_ENABLED,
)


LIMITS = {
    "auth_login": "10/minute",
    "auth_register": "5/minute",
    "auth_me": "100/minute",
    "partner_apply": "3/5minutes",
    "payment_intent": "20/minute",
    "booking_create": "30/minute",
    "order_create": "30/minute",
}
