"""Wishlist service — save/list/remove services per user."""

from sqlalchemy.orm import Session as DBSession

from app.models.service import Service
from app.models.tenant import Tenant
from app.models.wishlist import Wishlist


def add_to_wishlist(
    db: DBSession,
    *,
    user_id: str,
    service_id: str,
    note: str | None = None,
) -> tuple[Wishlist | None, str]:
    """Return (wishlist_row, status). status: 'ok' | 'already' | 'not_found'."""
    s = db.query(Service).filter(Service.id == service_id).one_or_none()
    if s is None:
        return None, "not_found"

    existing = (
        db.query(Wishlist)
        .filter(Wishlist.user_id == user_id, Wishlist.service_id == service_id)
        .one_or_none()
    )
    if existing is not None:
        return existing, "already"

    w = Wishlist(
        user_id=user_id,
        service_id=service_id,
        tenant_id=s.tenant_id,
        note=(note or "").strip() or None,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return w, "ok"


def remove_from_wishlist(db: DBSession, *, user_id: str, service_id: str) -> bool:
    row = (
        db.query(Wishlist)
        .filter(Wishlist.user_id == user_id, Wishlist.service_id == service_id)
        .one_or_none()
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def list_wishlist(db: DBSession, *, user_id: str) -> list[dict]:
    """Return enriched wishlist entries with service + tenant info."""
    rows = (
        db.query(Wishlist, Service, Tenant)
        .join(Service, Service.id == Wishlist.service_id)
        .join(Tenant, Tenant.id == Wishlist.tenant_id)
        .filter(Wishlist.user_id == user_id)
        .order_by(Wishlist.created_at.desc())
        .all()
    )
    out = []
    for w, s, t in rows:
        cfg = t.config or {}
        out.append({
            "wishlist_id": w.id,
            "service_id": s.id,
            "service_name": s.name,
            "service_type": s.type,
            "price": float(s.price),
            "currency": s.currency,
            "tenant_id": t.id,
            "tenant_slug": t.slug,
            "tenant_name": t.name,
            "location": cfg.get("location"),
            "rating": cfg.get("rating"),
            "cover_image": cfg.get("cover_image"),
            "note": w.note,
            "added_at": w.created_at.isoformat() if w.created_at else None,
        })
    return out


def is_wishlisted(db: DBSession, *, user_id: str, service_id: str) -> bool:
    row = (
        db.query(Wishlist)
        .filter(Wishlist.user_id == user_id, Wishlist.service_id == service_id)
        .one_or_none()
    )
    return row is not None


def count(db: DBSession, *, user_id: str) -> int:
    return db.query(Wishlist).filter(Wishlist.user_id == user_id).count()
