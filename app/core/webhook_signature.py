"""Generic HMAC-SHA256 verification for incoming provider webhooks.

Designed to be provider-agnostic so Telr/Stripe/others can all use it.
The generic format is:

    X-PlatformX-Signature: sha256=<hex>

Stripe uses a different header format (t=<ts>,v1=<sig>) and is handled
by verify_stripe_signature().
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Final

from fastapi import HTTPException, Request, status

STRIPE_TOLERANCE_SECONDS: Final[int] = 300


def _constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def verify_generic_signature(
    *,
    body: bytes,
    signature_header: str | None,
    secret: str,
) -> None:
    """Verify X-PlatformX-Signature: sha256=<hex>."""
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature",
        )
    if not signature_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature format",
        )
    provided = signature_header[len("sha256="):]
    expected = hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    if not _constant_time_compare(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )


def verify_stripe_signature(
    *,
    body: bytes,
    signature_header: str | None,
    secret: str,
) -> None:
    """Verify Stripe's Stripe-Signature header (t=<ts>,v1=<hex>)."""
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Stripe signature",
        )
    parts = dict(
        p.split("=", 1) for p in signature_header.split(",") if "=" in p
    )
    ts_raw = parts.get("t")
    v1 = parts.get("v1")
    if not ts_raw or not v1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Stripe signature format",
        )
    try:
        ts = int(ts_raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Stripe timestamp",
        )
    if abs(time.time() - ts) > STRIPE_TOLERANCE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Stripe signature timestamp out of tolerance",
        )
    signed_payload = f"{ts}.{body.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(
        secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()
    if not _constant_time_compare(v1, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Stripe signature",
        )


def verify_provider_webhook(
    *,
    provider: str,
    request: Request,
    body: bytes,
    secret: str,
) -> None:
    """Dispatch to the correct verifier based on provider name."""
    if provider.lower() == "stripe":
        verify_stripe_signature(
            body=body,
            signature_header=request.headers.get("stripe-signature"),
            secret=secret,
        )
    else:
        verify_generic_signature(
            body=body,
            signature_header=request.headers.get("x-platformx-signature"),
            secret=secret,
        )
