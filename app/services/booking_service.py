"""Booking service — DB operations for bookings."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.core.logging_config import get_logger
from app.models.service import Service
from app.schemas.booking import BookingCreate
from app.services import pricing_rules as pricing_rules_service

logger = get_logger(__name__)


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

    # Phase 37: rate plan override.
    # The rate plan's modifier is applied to the SERVICE base price,
    # not the client-supplied amount.
    rate_plan_id = None
    rate_plan_code = None
    if getattr(payload, "rate_plan_id", None) and payload.service_id:
        from app.models.rate_plan import RatePlan
        from app.services import rate_plan_service
        rp = (
            db.query(RatePlan)
            .filter(
                RatePlan.id == payload.rate_plan_id,
                RatePlan.tenant_id == tenant_id,
                RatePlan.service_id == payload.service_id,
                RatePlan.active.is_(True),
            )
            .one_or_none()
        )
        if rp is None:
            raise ValueError("rate_plan_id does not belong to this service or is inactive")
        service_for_plan = (
            db.query(Service)
            .filter(Service.id == payload.service_id, Service.tenant_id == tenant_id)
            .one_or_none()
        )
        plan_base = (
            Decimal(str(service_for_plan.price)) if service_for_plan is not None
            else base_amount
        )
        new_price, _delta = rate_plan_service.apply_plan_to_price(plan_base, rp)
        base_amount = new_price
        final_amount = new_price
        rate_plan_id = rp.id
        rate_plan_code = rp.code

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

    # Phase 38: promotion code (applied to the current base_amount).
    promotion_code = None
    promo_discount = Decimal("0.00")
    if getattr(payload, "promotion_code", None):
        from app.services import promotion_service
        p_code = payload.promotion_code.strip().lower()
        promo, reason = promotion_service.validate_promotion(
            db, tenant_id=tenant_id, code=p_code,
            base_amount=base_amount, user_id=user_id,
            service_id=payload.service_id,
        ) if False else (None, "placeholder")
        # Call with correct signature
        from app.models.tenant import Tenant as _T
        _t = db.query(_T).filter(_T.id == tenant_id).one_or_none()
        if _t is not None:
            promo, reason = promotion_service.validate_promotion(
                db, tenant=_t, code=p_code,
                base_amount=base_amount, user_id=user_id,
                service_id=payload.service_id,
            )
        if promo is None:
            raise ValueError(f"promotion: {reason}")
        new_amount, disc = promotion_service.apply_promotion(base_amount, promo)
        promo_discount = disc
        base_amount = new_amount
        final_amount = new_amount
        promotion_code = promo.code

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
        rate_plan_id=rate_plan_id,
        rate_plan_code=rate_plan_code,
        notes=payload.notes,
    )
    if promotion_code:
        tag = f"promo={promotion_code}"
        booking.notes = ((booking.notes or "") + "\n" + tag).strip()
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Phase 38: bump promotion usage count (best-effort).
    if promotion_code:
        try:
            from app.services import promotion_service
            from app.models.promotion import Promotion
            p_row = (
                db.query(Promotion)
                .filter(Promotion.tenant_id == tenant_id, Promotion.code == promotion_code)
                .one_or_none()
            )
            if p_row is not None:
                promotion_service.increment_usage(db, p_row)
        except Exception:
            logger.warning("Promotion usage increment failed for code %s", promotion_code, exc_info=True)

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
    # capture service_id + dates BEFORE commit for waitlist hook
    _svc_id = booking.service_id
    _ci = booking.check_in
    _co = booking.check_out

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)

    # best-effort waitlist notify (Phase 48, Step 4)
    try:
        from app.services import waitlist_service as _wls
        _wls.try_notify_after_cancel(db, service_id=_svc_id, check_in=_ci, check_out=_co)
    except Exception:
        logger.warning("Waitlist auto-notify failed", exc_info=True)

    return booking
