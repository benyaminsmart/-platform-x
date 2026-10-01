"""Installment service — create / list / pay installments.

Phase 57, Step 1.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.installment import Installment, InstallmentPlan
from app.models.payment import Payment


ALLOWED_N = (2, 3)

# Down-payment share by N (first installment gets the biggest slice)
DOWN_PAYMENT_SHARE = {2: Decimal("0.50"), 3: Decimal("0.40")}

# Default gap between due dates (days)
DUE_GAP_DAYS = 30


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _split(total: Decimal, n: int) -> list[Decimal]:
    """Split total into n parts; first gets the down-payment share."""
    total = _round2(total)
    first_share = DOWN_PAYMENT_SHARE.get(n, Decimal("1") / Decimal(n))
    first_amount = _round2(total * first_share)
    remaining = total - first_amount
    rest_n = n - 1
    if rest_n <= 0:
        return [total]
    base = _round2(remaining / Decimal(rest_n))
    parts = [first_amount] + [base] * rest_n
    # fix any rounding difference on the last installment
    diff = total - sum(parts)
    if diff != Decimal("0"):
        parts[-1] = _round2(parts[-1] + diff)
    return parts


def create_plan(
    db: DBSession,
    *,
    user_id: str,
    booking_id: str,
    n_installments: int = 2,
) -> tuple[InstallmentPlan | None, str]:
    """Create an installment plan for a booking.

    status: 'ok' | 'not_found' | 'bad_n' | 'already_paid' | 'exists'.
    """
    if n_installments not in ALLOWED_N:
        return None, "bad_n"

    b = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.user_id == user_id)
        .one_or_none()
    )
    if b is None:
        return None, "not_found"
    if b.payment_status == "paid":
        return None, "already_paid"

    existing = (
        db.query(InstallmentPlan)
        .filter(InstallmentPlan.booking_id == booking_id)
        .one_or_none()
    )
    if existing is not None:
        return existing, "exists"

    total = Decimal(str(b.total_amount or 0))
    if total <= 0:
        return None, "not_found"

    plan = InstallmentPlan(
        tenant_id=b.tenant_id,
        user_id=user_id,
        booking_id=b.id,
        total_amount=_round2(total),
        currency=b.currency,
        n_installments=n_installments,
        status="active",
    )
    db.add(plan)
    db.flush()  # get plan.id

    parts = _split(total, n_installments)
    today = date.today()
    for i, amount in enumerate(parts, start=1):
        due = today if i == 1 else today + timedelta(days=DUE_GAP_DAYS * (i - 1))
        # make due date relative to booking.check_in if it's near
        if b.check_in:
            # ensure last due is at most on check_in
            if due > b.check_in:
                due = b.check_in
        db.add(Installment(
            plan_id=plan.id,
            sequence=i,
            amount=amount,
            currency=b.currency,
            due_date=due,
            status="pending",
        ))

    db.commit()
    db.refresh(plan)
    return plan, "ok"


def list_plans(db: DBSession, *, user_id: str) -> list[dict]:
    rows = (
        db.query(InstallmentPlan)
        .filter(InstallmentPlan.user_id == user_id)
        .order_by(InstallmentPlan.created_at.desc())
        .all()
    )
    out: list[dict] = []
    for p in rows:
        items = (
            db.query(Installment)
            .filter(Installment.plan_id == p.id)
            .order_by(Installment.sequence.asc())
            .all()
        )
        out.append({
            "id": p.id,
            "booking_id": p.booking_id,
            "total_amount": float(p.total_amount),
            "currency": p.currency,
            "n_installments": p.n_installments,
            "status": p.status,
            "installments": [
                {
                    "id": i.id,
                    "sequence": i.sequence,
                    "amount": float(i.amount),
                    "currency": i.currency,
                    "due_date": i.due_date.isoformat() if i.due_date else None,
                    "status": i.status,
                    "paid_at": i.paid_at.isoformat() if i.paid_at else None,
                }
                for i in items
            ],
        })
    return out


def get_plan(db: DBSession, *, user_id: str, plan_id: str) -> InstallmentPlan | None:
    return (
        db.query(InstallmentPlan)
        .filter(InstallmentPlan.id == plan_id, InstallmentPlan.user_id == user_id)
        .one_or_none()
    )


def next_due(db: DBSession, *, plan_id: str) -> Installment | None:
    return (
        db.query(Installment)
        .filter(Installment.plan_id == plan_id, Installment.status == "pending")
        .order_by(Installment.sequence.asc())
        .first()
    )


def mark_paid(
    db: DBSession, *, user_id: str, installment_id: str, payment_id: str | None = None
) -> tuple[Installment | None, str]:
    """Mark a single installment paid. status: 'ok' | 'not_found' | 'already_paid'."""
    row = (
        db.query(Installment, InstallmentPlan)
        .join(InstallmentPlan, InstallmentPlan.id == Installment.plan_id)
        .filter(Installment.id == installment_id, InstallmentPlan.user_id == user_id)
        .one_or_none()
    )
    if row is None:
        return None, "not_found"
    inst, plan = row
    if inst.status == "paid":
        return inst, "already_paid"

    inst.status = "paid"
    inst.paid_at = _now()
    inst.payment_id = payment_id

    # check if all paid → complete the plan
    remaining = (
        db.query(Installment)
        .filter(
            Installment.plan_id == plan.id,
            Installment.id != inst.id,
            Installment.status != "paid",
        )
        .count()
    )
    if remaining == 0:
        plan.status = "completed"
        plan.completed_at = _now()

    db.commit()
    db.refresh(inst)
    return inst, "ok"


def cancel_plan(db: DBSession, *, user_id: str, plan_id: str) -> bool:
    row = (
        db.query(InstallmentPlan)
        .filter(InstallmentPlan.id == plan_id, InstallmentPlan.user_id == user_id)
        .one_or_none()
    )
    if row is None:
        return False
    if row.status == "completed":
        return False
    row.status = "cancelled"
    # cancel remaining installments
    pending = (
        db.query(Installment)
        .filter(Installment.plan_id == plan_id, Installment.status == "pending")
        .all()
    )
    for i in pending:
        i.status = "cancelled"
    db.commit()
    return True
