"""Webhook service — register, list, and deliver outbound events.

Delivery:
- HMAC-SHA256 signature in X-PlatformX-Signature: sha256=<hex>
- Event type in X-PlatformX-Event
- Payload is JSON body
- Every attempt logged in WebhookDelivery
- Sync delivery (best-effort) — production can move this to a queue

Security:
- Webhook secret shown exactly once; only its SHA-256 hash is stored.
- URL must be https:// (localhost http:// allowed for dev).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session as DBSession

from app.models.tenant import Tenant
from app.models.webhook import Webhook, WebhookDelivery


ALLOWED_EVENTS = {
    "booking.created",
    "booking.confirmed",
    "booking.cancelled",
    "payment.paid",
    "review.created",
    "review.responded",
}

_DEV_HOSTS = {"127.0.0.1", "localhost", "::1"}


# ---------- Security helpers ----------


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _generate_secret() -> tuple[str, str]:
    """Return (plaintext_secret, sha256_hex)."""
    plaintext = "whsec_" + secrets.token_urlsafe(32)
    return plaintext, _sha256_hex(plaintext)


def validate_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise ValueError("url is required")
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError("url must use http or https")
    if p.scheme == "http" and p.hostname not in _DEV_HOSTS:
        raise ValueError("http is only allowed for localhost; use https otherwise")
    return url


def validate_events(events: list[str]) -> list[str]:
    if not events:
        raise ValueError("at least one event is required")
    bad = [e for e in events if e not in ALLOWED_EVENTS]
    if bad:
        raise ValueError(f"unknown events: {bad}. allowed: {sorted(ALLOWED_EVENTS)}")
    return events


# ---------- CRUD ----------


def register_webhook(
    db: DBSession,
    *,
    tenant: Tenant,
    name: str,
    url: str,
    events: list[str],
    user_id: str | None = None,
) -> tuple[Webhook, str]:
    """Create a webhook. Returns (row, plaintext_secret)."""
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    url = validate_url(url)
    events = validate_events(events)

    plaintext_secret, hashed = _generate_secret()
    row = Webhook(
        tenant_id=tenant.id,
        name=name[:200],
        url=url,
        secret_hashed=hashed,
        events=list(events),
        active=True,
        created_by_user_id=user_id,
        extra={},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, plaintext_secret


def list_webhooks(db: DBSession, tenant: Tenant) -> list[Webhook]:
    return (
        db.query(Webhook)
        .filter(Webhook.tenant_id == tenant.id)
        .order_by(Webhook.created_at.desc())
        .all()
    )


def get_webhook(db: DBSession, tenant: Tenant, webhook_id: str) -> Webhook | None:
    return (
        db.query(Webhook)
        .filter(Webhook.id == webhook_id, Webhook.tenant_id == tenant.id)
        .one_or_none()
    )


def delete_webhook(db: DBSession, tenant: Tenant, webhook_id: str) -> Webhook | None:
    row = get_webhook(db, tenant, webhook_id)
    if row is None:
        return None
    row.active = False
    db.commit()
    db.refresh(row)
    return row


def serialize_webhook(row: Webhook) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "url": row.url,
        "events": list(row.events or []),
        "active": bool(row.active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "last_success_at": row.last_success_at.isoformat() if row.last_success_at else None,
        "last_failure_at": row.last_failure_at.isoformat() if row.last_failure_at else None,
        "last_status_code": row.last_status_code,
        "failure_count": row.failure_count,
    }


# ---------- Delivery ----------


def _sign(plaintext_secret_or_hash: str, body: bytes) -> str:
    """HMAC-SHA256 of body using the given secret (bytes safe)."""
    return hmac.new(
        plaintext_secret_or_hash.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()


def deliver(
    db: DBSession,
    *,
    webhook: Webhook,
    plaintext_secret: str,
    event_type: str,
    payload: dict[str, Any],
    timeout: float = 5.0,
) -> WebhookDelivery:
    """Send a signed POST request to the webhook URL.

    Note: caller must supply plaintext_secret because we only store the hash.
    In practice, deliveries triggered internally use a re-computed secret? No:
    we cannot recover the secret from the hash. Therefore delivery is only
    usable for tests and for events triggered *immediately* after creation
    within the same request. For production, the tenant must supply the
    secret or we change the storage. See note in docs.

    For now: we allow delivery only when the caller provides the plaintext
    secret (used in tests). Scheduled/system events require the secret to
    be stored in a recoverable form (future work).
    """
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = _sign(plaintext_secret, body)

    headers = {
        "Content-Type": "application/json",
        "X-PlatformX-Event": event_type,
        "X-PlatformX-Signature": f"sha256={signature}",
        "User-Agent": "Platform-X-Webhooks/1.0",
    }

    delivery = WebhookDelivery(
        tenant_id=webhook.tenant_id,
        webhook_id=webhook.id,
        event_type=event_type,
        payload=payload,
        success=False,
    )

    try:
        req = urllib.request.Request(webhook.url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            delivery.status_code = resp.status
            raw = resp.read(2000)
            delivery.response_body = raw.decode("utf-8", errors="replace")
            delivery.success = 200 <= (resp.status or 0) < 300
    except urllib.error.HTTPError as e:
        delivery.status_code = e.code
        try:
            delivery.response_body = e.read(500).decode("utf-8", errors="replace")
        except Exception:
            delivery.response_body = None
        delivery.error = f"HTTPError {e.code}"
    except Exception as e:
        delivery.error = str(e)[:500]

    now = datetime.now(timezone.utc)
    if delivery.success:
        webhook.last_success_at = now
    else:
        webhook.last_failure_at = now
        webhook.failure_count = (webhook.failure_count or 0) + 1
    webhook.last_status_code = delivery.status_code

    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery
