"""Booking tool — used by AI Booking Agent to actually book services."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.core.logging_config import get_logger
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User

logger = get_logger(__name__)



# Gemini tool definition
BOOKING_TOOL = {
    "type": "function",
    "name": "book_service",
    "description": (
        "Book a service for the current user. Use this when the user asks "
        "to book, reserve, or schedule something. Only call this AFTER "
        "confirming the service name, dates, and number of guests."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "service_name": {
                "type": "string",
                "description": "The name of the service to book (e.g. 'Standard Double', 'Hummus Beiruti')",
            },
            "check_in": {
                "type": "string",
                "description": "Check-in date in YYYY-MM-DD format",
            },
            "check_out": {
                "type": "string",
                "description": "Check-out date in YYYY-MM-DD format (optional)",
            },
            "guests": {
                "type": "integer",
                "description": "Number of guests (default 1)",
            },
            "notes": {
                "type": "string",
                "description": "Optional notes from the user",
            },
        },
        "required": ["service_name", "check_in"],
    },
}


class BookingToolError(Exception):
    """Raised when the tool cannot complete a booking."""


def find_service(db: DBSession, tenant_id: str, name: str) -> Service | None:
    """Find an active service by fuzzy name match."""
    # Exact match first
    exact = db.execute(
        select(Service).where(
            Service.tenant_id == tenant_id,
            Service.name == name,
            Service.status == "active",
        )
    ).scalar_one_or_none()
    if exact:
        return exact

    # Case-insensitive partial match
    ilike_pattern = f"%{name.lower()}%"
    stmt = select(Service).where(
        Service.tenant_id == tenant_id,
        Service.status == "active",
    )
    candidates = db.execute(stmt).scalars().all()
    for s in candidates:
        if name.lower() in s.name.lower() or s.name.lower() in name.lower():
            return s
    return None


def execute_book_service(
    db: DBSession,
    *,
    tenant_id: str,
    user: User,
    args: dict,
) -> dict:
    """Execute the book_service tool.

    Returns a dict result (for Gemini to read).
    Raises BookingToolError if not possible.
    """
    service_name = (args.get("service_name") or "").strip()
    check_in = (args.get("check_in") or "").strip()
    check_out = (args.get("check_out") or "").strip() or None
    guests = int(args.get("guests") or 1)
    notes = (args.get("notes") or "").strip() or None

    if not service_name:
        raise BookingToolError("service_name is required")
    if not check_in:
        raise BookingToolError("check_in date is required")

    # Parse dates
    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d").date()
        co = datetime.strptime(check_out, "%Y-%m-%d").date() if check_out else None
    except ValueError as exc:
        raise BookingToolError("Invalid date format. Use YYYY-MM-DD.") from exc

    # Find service
    svc = find_service(db, tenant_id, service_name)
    if svc is None:
        raise BookingToolError(
            f"Service '{service_name}' not found. Available types are on /services."
        )

    # Create booking
    amount = svc.price
    total = amount  # no discount
    booking = Booking(
        tenant_id=tenant_id,
        user_id=user.id,
        booking_type=svc.type,
        service_id=svc.id,
        service_name=svc.name,
        check_in=ci,
        check_out=co,
        guests=guests,
        amount=amount,
        discount=Decimal("0"),
        total_amount=total,
        currency=svc.currency,
        status="pending",
        payment_status="pending",
        notes=notes,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Notify business owners
    try:
        from app.services import notification_service
        staff_users = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.business_role.isnot(None),
            User.status == "active",
        ).all()
        for staff in staff_users:
            notification_service.create(
                db,
                tenant_id=tenant_id,
                user_id=staff.id,
                channel="in_app",
                template="new_booking",
                subject=f"New booking: {svc.name}",
                content=f"{user.first_name} {user.last_name} booked {svc.name} for {ci}.",
            )
    except Exception:
        logger.warning("Booking confirmation email failed", exc_info=True)

    return {
        "ok": True,
        "booking_id": booking.id,
        "service_name": svc.name,
        "check_in": str(ci),
        "check_out": str(co) if co else None,
        "guests": guests,
        "total": str(total),
        "currency": svc.currency,
        "payment_url": f"/payments/intent",
        "message": "Booking created. User must complete payment to confirm.",
    }
