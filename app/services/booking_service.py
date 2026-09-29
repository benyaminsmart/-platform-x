"""Booking service — DB operations for bookings."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.service import Service
from app.schemas.booking import BookingCreate
from app.services import pricing_rules as pricing_rules_service

# Statuses a user may still cancel
_CANCELLABLE = {"pending", "confirmed"}


def create_booking(
    db: DBSession,
    *,
    tenant_id: str,
    user_id: str,
    payload: BookingCreate,
) -> Booking:
    """Create a booking and compute total_amount.

    If payload.apply_pricing_rules is True and payload.service_id refers
    to a service owned by this tenant, dynamic pricing rules are applied
    (server-side) and each applied rule is recorded in the audit log.

    Otherwise, the payload amount is used as-is (legacy behavior).
    """
    base_amount = payload.amount
    discount = payload.discount
    final_amount: Decimal | None = None
    applied_rules: list[dict] = []

    if payload.apply_pricing_rules and payload.service_id:
        service = (
            db.query(Service)
            .filter(Service.id == payload.service_id, Service.tenant_id == tenant_id)
            .one_or_none()
        )
        if service is not None:
            preview = pricing_rules_service.preview_price(
                db,
                tenant_id=tenant_id,
                service=service,
                check_in=payload.check_in,
            )
            # Server-computed original price (from service), not client-provided.
            base_amount = Decimal(preview["original_price"])
            final_amount = Decimal(preview["final_price"])
            applied_rules = preview["applied_rules"]

            # Represent the difference as (positive) discount only when the
            # rules lowered the price; when rules increased the price we keep
            # discount at 0 and let total_amount reflect the increase.
            if final_amount < base_amount:
                discount = (base_amount - final_amount).quantize(Decimal("0.01"))
            else:
                discount = Decimal("0.00")

    # Total is authoritative: if rules produced a final amount, use it as-is.
    # Otherwise, legacy formula (base - discount).
    if final_amount is not None:
        total = final_amount.quantize(Decimal("0.01"))
    else:
        total = (base_amount - discount).quantize(Decimal("0.01"))

    booking = Booking(
        tenant_id=tenant_id,
        user_id=user_id,
        booking_type=payload.booking_type,
        service_id=payload.service_id,
        service_name=payload.service_name,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guests=payload.guests,
        amount=base_amount,
        discount=discount,
        total_amount=total,
        currency=payload.currency,
        status="pending",
        payment_status="pending",
        referral_code=payload.referral_code,
        notes=payload.notes,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Audit each applied rule against this booking (best-effort; must not
    # break the booking if it fails).
    if applied_rules:
        try:
            for r in applied_rules:
                pricing_rules_service.record_application(
                    db,
                    tenant_id=tenant_id,
                    rule_id=r["id"],
                    original_price=r["before"],
                    adjusted_price=r["after"],
                    delta_amount=r["delta_amount"],
                    delta_percent=r["delta_percent"],
                    currency=payload.currency,
                    service_id=payload.service_id,
                    booking_id=booking.id,
                    note=r.get("reason"),
                )
        except Exception:
            # Audit is non-critical; never fail the booking because of it.
            pass

    return booking


def get_booking(
    db: DBSession, *, user_id: str, booking_id: str, tenant_id: str | None = None
) -> Booking | None:
    """Return a booking owned by the user. tenant_id optional (cross-tenant when None)."""
    conditions = [Booking.id == booking_id, Booking.user_id == user_id]
    if tenant_id is not None:
        conditions.append(Booking.tenant_id == tenant_id)
    stmt = select(Booking).where(*conditions)
    return db.execute(stmt).scalar_one_or_none()


def list_bookings(
    db: DBSession,
    *,
    user_id: str,
    tenant_id: str | None = None,
    status: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Booking], int]:
    """Return (bookings, total_count) with filters and pagination.

    If tenant_id is None, returns bookings across all tenants for the user.
    """
    filters = [Booking.user_id == user_id]
    if tenant_id is not None:
        filters.append(Booking.tenant_id == tenant_id)
    if status:
        filters.append(Booking.status == status)
    if from_date:
        filters.append(Booking.check_in >= from_date)
    if to_date:
        filters.append(Booking.check_in <= to_date)

    total = db.execute(
        select(func.count()).select_from(Booking).where(*filters)
    ).scalar_one()

    stmt = (
        select(Booking)
        .where(*filters)
        .order_by(Booking.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = list(db.execute(stmt).scalars().all())
    return items, total


def cancel_booking(
    db: DBSession, *, user_id: str, booking_id: str, tenant_id: str | None = None
) -> Booking | None:
    """Cancel a booking if allowed. Returns None if not found.

    Raises ValueError if the booking is not in a cancellable state.
    """
    booking = get_booking(db, user_id=user_id, booking_id=booking_id, tenant_id=tenant_id)
    if booking is None:
        return None
    if booking.status not in _CANCELLABLE:
        raise ValueError(f"Booking in status '{booking.status}' cannot be cancelled")
    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)
    return booking
