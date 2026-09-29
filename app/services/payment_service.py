"""Payment service — DB operations + provider orchestration."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.order import Order
from app.models.payment import Payment
from app.schemas.payment import PaymentIntentRequest
from app.services.payment_provider import get_payment_provider


def _get_owned_booking(
    db: DBSession, *, tenant_id: str, user_id: str, booking_id: str
) -> Booking | None:
    return db.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.tenant_id == tenant_id,
            Booking.user_id == user_id,
        )
    ).scalar_one_or_none()


def _get_owned_order(
    db: DBSession, *, tenant_id: str, user_id: str, order_id: str
) -> Order | None:
    return db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.tenant_id == tenant_id,
            Order.user_id == user_id,
        )
    ).scalar_one_or_none()


def create_intent(
    db: DBSession,
    *,
    tenant_id: str,
    user_id: str,
    payload: PaymentIntentRequest,
) -> tuple[Payment, str]:
    """Create a payment intent.

    Returns (payment, redirect_url). Raises ValueError when the target
    booking/order is missing or already paid.
    """
    # Validate target belongs to user
    if payload.booking_id:
        target = _get_owned_booking(
            db, tenant_id=tenant_id, user_id=user_id, booking_id=payload.booking_id
        )
        if target is None:
            raise ValueError("Booking not found")
        if target.payment_status == "paid":
            raise ValueError("Booking already paid")
    else:
        target = _get_owned_order(
            db, tenant_id=tenant_id, user_id=user_id, order_id=payload.order_id  # type: ignore[arg-type]
        )
        if target is None:
            raise ValueError("Order not found")
        if target.payment_status == "paid":
            raise ValueError("Order already paid")

    provider = get_payment_provider()
    intent = provider.create_intent(
        amount=payload.amount,
        currency=payload.currency,
        method=payload.method,
        description=f"Payment for {payload.booking_id or payload.order_id}",
    )

    payment = Payment(
        tenant_id=tenant_id,
        user_id=user_id,
        booking_id=payload.booking_id,
        order_id=payload.order_id,
        amount=payload.amount,
        currency=payload.currency,
        provider=provider.name,
        provider_reference=intent.provider_reference,
        status="pending",
        method=payload.method,
        metadata_json={"redirect_url": intent.redirect_url},
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment, intent.redirect_url


def get_payment(
    db: DBSession, *, tenant_id: str, user_id: str, payment_id: str
) -> Payment | None:
    """Return a payment owned by the user."""
    return db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.tenant_id == tenant_id,
            Payment.user_id == user_id,
        )
    ).scalar_one_or_none()


def mark_success(
    db: DBSession, *, provider_reference: str, raw: dict | None = None
) -> Payment | None:
    """Mark a payment as successful (called by webhook or mock confirm).

    Side effect: update target booking/order payment_status to 'paid'.
    """
    payment = db.execute(
        select(Payment).where(Payment.provider_reference == provider_reference)
    ).scalar_one_or_none()
    if payment is None:
        return None
    if payment.status == "success":
        return payment  # idempotent

    payment.status = "success"
    payment.completed_at = datetime.now(timezone.utc)
    if raw is not None:
        payment.metadata_json = {**payment.metadata_json, "webhook": raw}

    if payment.booking_id:
        booking = db.execute(
            select(Booking).where(Booking.id == payment.booking_id)
        ).scalar_one_or_none()
        if booking is not None:
            booking.payment_status = "paid"
            if booking.status == "pending":
                booking.status = "confirmed"

            # Auto-assign a physical room if the service has rooms and none
            # is assigned yet (best-effort; never fails the payment).
            if not booking.room_number and booking.service_id:
                try:
                    from app.models.tenant import Tenant as _T2
                    from app.services import room_service
                    _t2 = db.query(_T2).filter(_T2.id == payment.tenant_id).one_or_none()
                    if _t2 is not None:
                        out = room_service.assign_room_to_booking(
                            db, tenant=_t2, booking=booking, room=None
                        )
                        if out.get("ok"):
                            booking.room_number = out["room_number"]
                            db.add(booking)
                            db.commit()
                            db.refresh(booking)
                except Exception:
                    # Never fail the payment because of room assignment issues.
                    pass

            # Award points: 1 point per 10 currency units (min 5 points)
            from app.services import reward_service
            points = max(5, int(float(booking.total_amount) / 10))
            reward_service.add_points(
                db,
                tenant_id=payment.tenant_id,
                user_id=payment.user_id,
                points=points,
                reward_type="earn",
                description=f"Booking: {booking.service_name}",
                reference_id=booking.id,
            )

            # Record booking notification + send email (both non-blocking)
            try:
                from app.models.tenant import Tenant as _T
                from app.models.user import User as _U
                from app.services import notification_service
                _user = db.query(_U).filter(_U.id == payment.user_id).one_or_none()
                _tenant = db.query(_T).filter(_T.id == payment.tenant_id).one_or_none()
                if _user and _tenant:
                    notification_service.create(
                        db,
                        tenant_id=payment.tenant_id,
                        user_id=payment.user_id,
                        channel="in_app",
                        template="booking_confirmed",
                        subject=f"Booking confirmed — {_tenant.name}",
                        content=f"Your booking for {booking.service_name} at {_tenant.name} is confirmed.",
                    )
                    notification_service.send_booking_confirmed_email(
                        to_email=_user.email,
                        user_name=_user.first_name,
                        tenant_name=_tenant.name,
                        service_name=booking.service_name,
                        check_in=str(booking.check_in),
                        check_out=str(booking.check_out) if booking.check_out else None,
                        guests=booking.guests,
                        total=str(booking.total_amount),
                        currency=booking.currency,
                        account_url=f"/{_tenant.slug}/account",
                    )

                    # Notify business owners/staff
                    try:
                        staff_users = db.query(_U).filter(
                            _U.tenant_id == payment.tenant_id,
                            _U.business_role.isnot(None),
                            _U.status == "active",
                        ).all()
                        for staff in staff_users:
                            notification_service.create(
                                db,
                                tenant_id=payment.tenant_id,
                                user_id=staff.id,
                                channel="in_app",
                                template="new_booking",
                                subject=f"New booking: {booking.service_name}",
                                content=f"{_user.first_name} {_user.last_name} booked {booking.service_name} for {booking.check_in}.",
                            )
                    except Exception:
                        pass
            except Exception:
                pass
    if payment.order_id:
        order = db.execute(
            select(Order).where(Order.id == payment.order_id)
        ).scalar_one_or_none()
        if order is not None:
            order.payment_status = "paid"
            # Award points for orders too
            from app.services import reward_service
            points = max(3, int(float(order.amount) / 10))
            reward_service.add_points(
                db,
                tenant_id=payment.tenant_id,
                user_id=payment.user_id,
                points=points,
                reward_type="earn",
                description=f"Order: {order.service_name}",
                reference_id=order.id,
            )

    db.commit()
    db.refresh(payment)
    return payment


def mark_failed(
    db: DBSession, *, provider_reference: str, raw: dict | None = None
) -> Payment | None:
    """Mark a payment as failed (webhook path)."""
    payment = db.execute(
        select(Payment).where(Payment.provider_reference == provider_reference)
    ).scalar_one_or_none()
    if payment is None:
        return None
    if payment.status in {"success", "refunded"}:
        return payment
    payment.status = "failed"
    if raw is not None:
        payment.metadata_json = {**payment.metadata_json, "webhook": raw}
    db.commit()
    db.refresh(payment)
    return payment
