"""Group booking service — manage members + share validation.

Rules:
- Only the booking's owner can add/remove members.
- Only bookings with is_group=True accept members.
- Share sum may not exceed the booking total_amount.
- Email unique per booking (enforced at DB level, mirrored here).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.group_member import GroupMember


MAX_MEMBERS = 50


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def list_members(db: DBSession, *, booking_id: str) -> list[GroupMember]:
    return (
        db.query(GroupMember)
        .filter(GroupMember.booking_id == booking_id)
        .order_by(GroupMember.created_at.asc())
        .all()
    )


def get_member(db: DBSession, *, booking_id: str, member_id: str) -> GroupMember | None:
    return (
        db.query(GroupMember)
        .filter(GroupMember.id == member_id, GroupMember.booking_id == booking_id)
        .one_or_none()
    )


def add_member(
    db: DBSession,
    *,
    booking: Booking,
    name: str,
    email: str,
    share_amount: float | Decimal = 0,
    note: str | None = None,
) -> GroupMember:
    if not booking.is_group:
        raise ValueError("booking is not marked as a group")
    name = (name or "").strip()
    email = (email or "").strip().lower()
    if not name:
        raise ValueError("name is required")
    if not email or "@" not in email:
        raise ValueError("valid email is required")

    existing_count = db.query(func.count(GroupMember.id)).filter(
        GroupMember.booking_id == booking.id
    ).scalar() or 0
    if existing_count >= MAX_MEMBERS:
        raise ValueError(f"max {MAX_MEMBERS} members per booking")

    dup = (
        db.query(GroupMember)
        .filter(GroupMember.booking_id == booking.id, GroupMember.email == email)
        .one_or_none()
    )
    if dup is not None:
        raise ValueError("this email is already a member of this booking")

    share = _round2(Decimal(str(share_amount or 0)))
    if share < 0:
        raise ValueError("share_amount cannot be negative")

    # validate total shares <= booking total_amount
    current_sum = (
        db.query(func.coalesce(func.sum(GroupMember.share_amount), 0))
        .filter(GroupMember.booking_id == booking.id)
        .scalar()
        or 0
    )
    total_booking = Decimal(str(booking.total_amount or 0))
    if Decimal(str(current_sum)) + share > total_booking:
        raise ValueError(
            f"total shares ({Decimal(str(current_sum)) + share}) "
            f"would exceed booking total ({total_booking})"
        )

    m = GroupMember(
        tenant_id=booking.tenant_id,
        booking_id=booking.id,
        name=name,
        email=email,
        share_amount=share,
        paid=False,
        note=(note or "").strip() or None,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def update_member(
    db: DBSession,
    *,
    booking: Booking,
    member_id: str,
    updates: dict,
) -> GroupMember | None:
    m = get_member(db, booking_id=booking.id, member_id=member_id)
    if m is None:
        return None

    if "name" in updates and updates["name"] is not None:
        v = str(updates["name"]).strip()
        if not v:
            raise ValueError("name cannot be empty")
        m.name = v
    if "email" in updates and updates["email"] is not None:
        v = str(updates["email"]).strip().lower()
        if "@" not in v:
            raise ValueError("valid email is required")
        dup = (
            db.query(GroupMember)
            .filter(
                GroupMember.booking_id == booking.id,
                GroupMember.email == v,
                GroupMember.id != m.id,
            )
            .one_or_none()
        )
        if dup is not None:
            raise ValueError("this email is already a member of this booking")
        m.email = v
    if "share_amount" in updates and updates["share_amount"] is not None:
        new_share = _round2(Decimal(str(updates["share_amount"])))
        if new_share < 0:
            raise ValueError("share_amount cannot be negative")
        # ensure new total does not exceed booking total
        others_sum = (
            db.query(func.coalesce(func.sum(GroupMember.share_amount), 0))
            .filter(GroupMember.booking_id == booking.id, GroupMember.id != m.id)
            .scalar()
            or 0
        )
        total_booking = Decimal(str(booking.total_amount or 0))
        if Decimal(str(others_sum)) + new_share > total_booking:
            raise ValueError("total shares would exceed booking total")
        m.share_amount = new_share
    if "paid" in updates and updates["paid"] is not None:
        m.paid = bool(updates["paid"])
    if "note" in updates:
        v = updates["note"]
        m.note = (str(v).strip() if v else None) or None

    db.commit()
    db.refresh(m)
    return m


def remove_member(db: DBSession, *, booking: Booking, member_id: str) -> bool:
    m = get_member(db, booking_id=booking.id, member_id=member_id)
    if m is None:
        return False
    db.delete(m)
    db.commit()
    return True


def share_summary(db: DBSession, *, booking: Booking) -> dict:
    members = list_members(db, booking_id=booking.id)
    total_booking = Decimal(str(booking.total_amount or 0))
    total_share = sum((Decimal(str(m.share_amount or 0)) for m in members), Decimal("0"))
    paid_share = sum(
        (Decimal(str(m.share_amount or 0)) for m in members if m.paid),
        Decimal("0"),
    )
    return {
        "booking_total": str(_round2(total_booking)),
        "shares_total": str(_round2(total_share)),
        "paid_total": str(_round2(paid_share)),
        "unpaid_total": str(_round2(total_share - paid_share)),
        "remaining_to_allocate": str(_round2(total_booking - total_share)),
        "members_count": len(members),
        "paid_members_count": sum(1 for m in members if m.paid),
    }
