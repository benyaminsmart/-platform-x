"""Business Group service — create groups, attach tenants, aggregate metrics.

Phase 58, Step 1.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.business_group import BusinessGroup
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


_PAID_STATUSES = ("confirmed", "paid")


def _slugify(name: str) -> str:
    import re
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:80] or "group"


def _unique_slug(db: DBSession, base: str) -> str:
    slug = base
    i = 2
    while db.query(BusinessGroup).filter(BusinessGroup.slug == slug).one_or_none() is not None:
        slug = f"{base}-{i}"
        i += 1
    return slug


def create_group(
    db: DBSession, *, owner_user_id: str, name: str
) -> tuple[BusinessGroup | None, str]:
    name = (name or "").strip()
    if not name:
        return None, "bad_name"
    slug = _unique_slug(db, _slugify(name))
    g = BusinessGroup(slug=slug, name=name, owner_user_id=owner_user_id)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g, "ok"


def list_groups(db: DBSession, *, owner_user_id: str) -> list[dict]:
    rows = (
        db.query(BusinessGroup)
        .filter(BusinessGroup.owner_user_id == owner_user_id)
        .order_by(BusinessGroup.created_at.desc())
        .all()
    )
    out = []
    for g in rows:
        members = db.query(Tenant).filter(Tenant.group_id == g.id).all()
        out.append({
            "id": g.id,
            "slug": g.slug,
            "name": g.name,
            "members_count": len(members),
            "members": [
                {"id": t.id, "slug": t.slug, "name": t.name,
                 "category": (t.config or {}).get("type")}
                for t in members
            ],
        })
    return out


def attach_tenant(
    db: DBSession, *, owner_user_id: str, group_id: str, tenant_slug: str
) -> tuple[Tenant | None, str]:
    """Attach a tenant to a group. Verifies the owner owns the tenant
    (via a User with business_role=owner for that tenant)."""
    g = (
        db.query(BusinessGroup)
        .filter(BusinessGroup.id == group_id, BusinessGroup.owner_user_id == owner_user_id)
        .one_or_none()
    )
    if g is None:
        return None, "not_found"

    t = db.query(Tenant).filter(Tenant.slug == tenant_slug).one_or_none()
    if t is None:
        return None, "tenant_not_found"

    # verify ownership: a user with business_role=owner in that tenant whose
    # email matches the group owner's email, OR the same user id
    owner = db.query(User).filter(User.id == owner_user_id).one_or_none()
    if owner is None:
        return None, "not_found"
    same_tenant_owner = (
        db.query(User)
        .filter(
            User.tenant_id == t.id,
            User.business_role == "owner",
            User.email == owner.email,
        )
        .one_or_none()
    )
    if same_tenant_owner is None and owner.tenant_id != t.id:
        return None, "not_owner"

    t.group_id = g.id
    db.commit()
    db.refresh(t)
    return t, "ok"


def detach_tenant(
    db: DBSession, *, owner_user_id: str, group_id: str, tenant_slug: str
) -> bool:
    g = (
        db.query(BusinessGroup)
        .filter(BusinessGroup.id == group_id, BusinessGroup.owner_user_id == owner_user_id)
        .one_or_none()
    )
    if g is None:
        return False
    t = (
        db.query(Tenant)
        .filter(Tenant.slug == tenant_slug, Tenant.group_id == g.id)
        .one_or_none()
    )
    if t is None:
        return False
    t.group_id = None
    db.commit()
    return True


def delete_group(db: DBSession, *, owner_user_id: str, group_id: str) -> bool:
    g = (
        db.query(BusinessGroup)
        .filter(BusinessGroup.id == group_id, BusinessGroup.owner_user_id == owner_user_id)
        .one_or_none()
    )
    if g is None:
        return False
    # detach all tenants first
    members = db.query(Tenant).filter(Tenant.group_id == g.id).all()
    for t in members:
        t.group_id = None
    db.delete(g)
    db.commit()
    return True


def aggregate_metrics(db: DBSession, *, group_id: str, window_days: int = 30) -> dict[str, Any]:
    """Aggregate metrics across all tenants in the group."""
    members = db.query(Tenant).filter(Tenant.group_id == group_id).all()
    if not members:
        return {
            "members_count": 0,
            "services_count": 0,
            "bookings_30d": 0,
            "revenue_30d": "0.00",
            "avg_rating": None,
            "currency": None,
        }

    tenant_ids = [t.id for t in members]
    since = date.today() - timedelta(days=window_days)

    services_count = int(
        db.query(func.count(Service.id))
        .filter(Service.tenant_id.in_(tenant_ids), Service.status == "active")
        .scalar() or 0
    )

    bookings_q = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.tenant_id.in_(tenant_ids),
            Booking.status.in_(list(_PAID_STATUSES)),
            Booking.check_in >= since,
        )
    )
    bookings_30d = int(bookings_q.scalar() or 0)

    revenue = (
        db.query(func.sum(Booking.total_amount))
        .filter(
            Booking.tenant_id.in_(tenant_ids),
            Booking.status.in_(list(_PAID_STATUSES)),
            Booking.check_in >= since,
        )
        .scalar()
    )
    revenue_dec = Decimal(str(revenue)) if revenue is not None else Decimal("0")
    currency = None
    # currency: take from first member with a currency configured
    for t in members:
        c = (t.config or {}).get("currency")
        if c:
            currency = c
            break
    if currency is None:
        currency = "AED"

    # avg rating from tenant config
    ratings = []
    for t in members:
        r = (t.config or {}).get("rating")
        try:
            if r is not None:
                ratings.append(float(r))
        except (TypeError, ValueError):
            pass
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    return {
        "members_count": len(members),
        "services_count": services_count,
        "bookings_30d": bookings_30d,
        "revenue_30d": str(revenue_dec.quantize(Decimal("0.01"))),
        "avg_rating": avg_rating,
        "currency": currency,
    }
