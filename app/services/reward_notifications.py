"""Reward Notification Service.

Phase 78, Step 2 (plan §14).

Handles the two notification flows around expiration:
- Pre-expiry: notify the user 7 / 3 / 1 days before expiration.
- Post-expiry: notify the user after the reward has expired.

Notifications go through `notification_service.create` (in-app) and,
where an email template exists, an email send.

This module does NOT change any ledger state. It only reads and
notifies. Idempotency is ensured by a `_notified_<window>d` marker in
each reward's `extra` dict.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session as DBSession

from app.core import rewards_config
from app.core.logging_config import get_logger
from app.models.reward import Reward
from app.services import notification_service, reward_expiration

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mark(reward: Reward, key: str) -> None:
    extra = dict(reward.extra or {})
    extra[key] = _now().isoformat()
    reward.extra = extra


def notify_expiring_soon(db: DBSession, *, tenant_id: str | None = None) -> dict:
    """Send pre-expiry notifications for the configured windows.

    Windows come from `rewards_config.EXPIRATION_NOTIFY_DAYS_BEFORE`
    (default 7 / 3 / 1). For each reward, we check every window and
    send at most one notification per window (tracked in `extra`).
    """
    sent = 0
    skipped = 0
    errors = 0
    windows = getattr(rewards_config, "EXPIRATION_NOTIFY_DAYS_BEFORE", (7, 3, 1))

    for window in windows:
        rows = reward_expiration.find_expiring_soon(
            db, tenant_id=tenant_id, days_before=window
        )
        for r in rows:
            marker_key = f"_notified_{window}d"
            if (r.extra or {}).get(marker_key):
                skipped += 1
                continue
            try:
                notification_service.create(
                    db,
                    tenant_id=r.tenant_id,
                    user_id=r.user_id,
                    channel="in_app",
                    template="reward_expiring_soon",
                    subject=f"Your reward expires in {window} days",
                    content=(
                        f"You have a reward of {r.amount} {r.currency} "
                        f"expiring in {window} days. Use it before it expires."
                    ),
                )
                _mark(r, marker_key)
                db.add(r)
                db.commit()
                sent += 1
            except Exception:
                errors += 1
                logger.exception("failed to notify reward %s", r.id)

    return {"sent": sent, "skipped": skipped, "errors": errors}


def notify_expired(db: DBSession, *, tenant_id: str | None = None) -> dict:
    """Send notifications for rewards that have already expired.

    Idempotent via `_notified_expired` marker.
    """
    sent = 0
    skipped = 0
    errors = 0

    q = db.query(Reward).filter(
        Reward.status == "AVAILABLE",
        Reward.expires_at.isnot(None),
        Reward.expires_at <= _now(),
    )
    if tenant_id is not None:
        q = q.filter(Reward.tenant_id == tenant_id)
    q = q.limit(1000)

    for r in q.all():
        if (r.extra or {}).get("_notified_expired"):
            skipped += 1
            continue
        if (r.extra or {}).get("_expired") is not True:
            # not yet processed by the expiration job
            skipped += 1
            continue
        try:
            notification_service.create(
                db,
                tenant_id=r.tenant_id,
                user_id=r.user_id,
                channel="in_app",
                template="reward_expired",
                subject="Your reward has expired",
                content=(
                    f"Your reward of {r.amount} {r.currency} has expired."
                ),
            )
            _mark(r, "_notified_expired")
            db.add(r)
            db.commit()
            sent += 1
        except Exception:
            errors += 1
            logger.exception("failed to notify expired reward %s", r.id)

    return {"sent": sent, "skipped": skipped, "errors": errors}
