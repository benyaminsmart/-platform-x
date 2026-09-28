"""Audit service — write and read audit log entries."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.audit_log import AuditLog


def log(
    db: DBSession,
    *,
    actor_id: str,
    actor_type: str,
    action: str,
    tenant_id: str | None = None,
    target_table: str | None = None,
    target_id: str | None = None,
    changes: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Write an audit log entry."""
    entry = AuditLog(
        actor_id=actor_id,
        actor_type=actor_type,
        tenant_id=tenant_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_entries(
    db: DBSession,
    *,
    tenant_id: str | None = None,
    actor_id: str | None = None,
    action: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[AuditLog], int]:
    """Return (entries, total) with filters."""
    filters = []
    if tenant_id:
        filters.append(AuditLog.tenant_id == tenant_id)
    if actor_id:
        filters.append(AuditLog.actor_id == actor_id)
    if action:
        filters.append(AuditLog.action == action)

    total = db.execute(
        select(func.count()).select_from(AuditLog).where(*filters)
    ).scalar_one()

    stmt = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all()), total
