"""Reports service — CSV exports for business panel.

Design:
- CSV via Python's built-in csv module (no dependency).
- All exports tenant-scoped.
- Money preserved as string to keep precision in spreadsheets.
"""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User


_EXCLUDED_STATUSES = ("cancelled",)


def _csv(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def bookings_csv(db: DBSession, tenant: Tenant, *, days: int = 90) -> str:
    days = max(1, min(int(days), 3650))
    from_d = date.today() - timedelta(days=days)
    rows = (
        db.query(Booking)
        .filter(Booking.tenant_id == tenant.id, Booking.check_in >= from_d)
        .order_by(Booking.check_in.desc())
        .all()
    )
    user_ids = list({b.user_id for b in rows})
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    out: list[list] = []
    for b in rows:
        u = users.get(b.user_id)
        customer = f"{(u.first_name or '')} {(u.last_name or '')}".strip() if u else ""
        out.append([
            b.id,
            str(b.check_in),
            str(b.check_out) if b.check_out else "",
            b.booking_type,
            b.service_name,
            b.guests,
            str(b.amount),
            str(b.discount),
            str(b.total_amount),
            b.currency,
            b.status,
            b.payment_status,
            customer,
            (u.email if u else ""),
            b.created_at.isoformat() if b.created_at else "",
        ])
    return _csv(
        ["booking_id", "check_in", "check_out", "type", "service",
         "guests", "amount", "discount", "total", "currency",
         "status", "payment_status", "customer_name", "customer_email",
         "created_at"],
        out,
    )


def customers_csv(db: DBSession, tenant: Tenant, *, limit: int = 5000) -> str:
    from sqlalchemy import func

    limit = max(1, min(int(limit), 10000))
    rows = (
        db.query(
            Booking.user_id,
            func.count(Booking.id).label("cnt"),
            func.coalesce(func.sum(Booking.total_amount), 0).label("total"),
        )
        .filter(Booking.tenant_id == tenant.id, Booking.status.notin_(_EXCLUDED_STATUSES))
        .group_by(Booking.user_id)
        .order_by(func.count(Booking.id).desc())
        .limit(limit)
        .all()
    )
    header = ["customer_id", "name", "email", "phone", "tier", "points", "bookings", "total_spent"]
    if not rows:
        return _csv(header, [])
    user_ids = [r[0] for r in rows]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    out: list[list] = []
    for uid, cnt, total in rows:
        u = users.get(uid)
        if not u:
            continue
        name = f"{(u.first_name or '')} {(u.last_name or '')}".strip()
        out.append([u.id, name, u.email, u.phone or "", u.tier, u.points, int(cnt), str(total)])
    return _csv(header, out)


def revenue_summary_csv(db: DBSession, tenant: Tenant, *, days: int = 90) -> str:
    from sqlalchemy import func

    days = max(1, min(int(days), 3650))
    from_d = date.today() - timedelta(days=days)
    rows = (
        db.query(
            Booking.check_in,
            func.count(Booking.id).label("cnt"),
            func.coalesce(func.sum(Booking.total_amount), 0).label("rev"),
        )
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.check_in >= from_d,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.payment_status == "paid",
        )
        .group_by(Booking.check_in)
        .order_by(Booking.check_in.desc())
        .all()
    )
    out = [[str(r[0]), int(r[1]), str(r[2])] for r in rows]
    return _csv(["date", "paid_bookings", "revenue"], out)
