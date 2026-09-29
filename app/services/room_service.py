"""Room service — CRUD + availability + auto-assignment."""

from datetime import date, timedelta

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.room import Room
from app.models.tenant import Tenant


VALID_STATUSES = {"available", "occupied", "maintenance", "inactive"}


def list_rooms(
    db: DBSession,
    tenant: Tenant,
    *,
    status_filter: str | None = None,
    service_id: str | None = None,
) -> list[Room]:
    q = db.query(Room).filter(Room.tenant_id == tenant.id)
    if status_filter:
        q = q.filter(Room.status == status_filter)
    if service_id:
        q = q.filter(Room.service_id == service_id)
    return q.order_by(Room.number).all()


def get_room(db: DBSession, tenant: Tenant, room_id: str) -> Room | None:
    return (
        db.query(Room)
        .filter(Room.id == room_id, Room.tenant_id == tenant.id)
        .one_or_none()
    )


def create_room(
    db: DBSession,
    tenant: Tenant,
    *,
    number: str,
    service_id: str | None = None,
    floor: int | None = None,
    type: str | None = None,
    status: str = "available",
    notes: str | None = None,
) -> Room:
    number = (number or "").strip()
    if not number:
        raise ValueError("number is required")
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of: {sorted(VALID_STATUSES)}")
    if service_id:
        from app.models.service import Service
        s = db.query(Service).filter(Service.id == service_id, Service.tenant_id == tenant.id).one_or_none()
        if s is None:
            raise ValueError("service not found for this tenant")
    existing = (
        db.query(Room)
        .filter(Room.tenant_id == tenant.id, Room.number == number)
        .one_or_none()
    )
    if existing is not None:
        raise ValueError(f"room number '{number}' already exists")

    r = Room(
        tenant_id=tenant.id,
        service_id=service_id,
        number=number,
        floor=floor,
        type=(type or "").strip() or None,
        status=status,
        notes=(notes or "").strip() or None,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def update_room(
    db: DBSession,
    tenant: Tenant,
    room_id: str,
    *,
    updates: dict,
) -> Room | None:
    r = get_room(db, tenant, room_id)
    if r is None:
        return None
    for k, v in updates.items():
        if k == "status" and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of: {sorted(VALID_STATUSES)}")
        if k == "number":
            v = (v or "").strip()
            if not v:
                raise ValueError("number cannot be empty")
            other = (
                db.query(Room)
                .filter(Room.tenant_id == tenant.id, Room.number == v, Room.id != r.id)
                .one_or_none()
            )
            if other is not None:
                raise ValueError(f"room number '{v}' already exists")
        if hasattr(r, k):
            setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


def delete_room(db: DBSession, tenant: Tenant, room_id: str) -> Room | None:
    r = get_room(db, tenant, room_id)
    if r is None:
        return None
    r.status = "inactive"
    db.commit()
    db.refresh(r)
    return r


# ---------- Auto-assignment ----------


def find_available_room_for_booking(
    db: DBSession,
    *,
    tenant: Tenant,
    booking: Booking,
) -> Room | None:
    """Find a room of the same service not overlapping the booking window."""
    if not booking.service_id:
        return None

    candidates = (
        db.query(Room)
        .filter(
            Room.tenant_id == tenant.id,
            Room.service_id == booking.service_id,
            Room.status == "available",
        )
        .order_by(Room.number)
        .all()
    )
    if not candidates:
        return None

    co = booking.check_out or (booking.check_in + timedelta(days=1))
    overlapping = (
        db.query(Booking)
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.service_id == booking.service_id,
            Booking.status.notin_(("cancelled", "no_show")),
            Booking.room_number.isnot(None),
            Booking.check_in < co,
            Booking.id != booking.id,
        )
        .all()
    )
    busy_room_numbers = set()
    for b in overlapping:
        end = b.check_out or (b.check_in + timedelta(days=1))
        if end > booking.check_in:
            busy_room_numbers.add(b.room_number)

    for room in candidates:
        if room.number not in busy_room_numbers:
            return room
    return None


def assign_room_to_booking(
    db: DBSession,
    *,
    tenant: Tenant,
    booking: Booking,
    room: Room | None = None,
) -> dict:
    """Assign a room to a booking. If room is None, auto-pick."""
    if room is None:
        room = find_available_room_for_booking(db, tenant=tenant, booking=booking)
    if room is None:
        return {"ok": False, "reason": "no room available for this service"}

    if room.tenant_id != tenant.id:
        return {"ok": False, "reason": "room belongs to another tenant"}
    if room.status != "available":
        return {"ok": False, "reason": f"room status is '{room.status}'"}
    if booking.service_id and room.service_id and room.service_id != booking.service_id:
        return {"ok": False, "reason": "room's service does not match booking's service"}

    booking.room_number = room.number
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return {"ok": True, "booking_id": booking.id, "room_number": room.number}
