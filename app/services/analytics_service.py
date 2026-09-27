"""Analytics service — record and query events."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.analytics_event import AnalyticsEvent


def track(
    db: DBSession,
    *,
    tenant_id: str,
    event_type: str,
    user_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AnalyticsEvent:
    """Record an analytics event."""
    event = AnalyticsEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        metadata_json=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def counts_by_type(
    db: DBSession, *, tenant_id: str, top: int = 20
) -> list[tuple[str, int]]:
    """Return (event_type, count) sorted desc, limited to top N."""
    stmt = (
        select(AnalyticsEvent.event_type, func.count().label("c"))
        .where(AnalyticsEvent.tenant_id == tenant_id)
        .group_by(AnalyticsEvent.event_type)
        .order_by(func.count().desc())
        .limit(top)
    )
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def total_events(db: DBSession, *, tenant_id: str) -> int:
    return db.execute(
        select(func.count()).select_from(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id
        )
    ).scalar_one()
