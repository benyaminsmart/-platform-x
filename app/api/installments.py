"""Installment API (Phase 57, Step 2).

  GET    /me/installment-plans                      list user's plans
  POST   /me/installment-plans                      create a plan for a booking
  GET    /me/installment-plans/{plan_id}            plan detail
  POST   /me/installment-plans/installments/{id}/pay   mark an installment paid
  DELETE /me/installment-plans/{plan_id}            cancel a plan

NOTE: no 'from __future__ import annotations' in this file.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services import installment_service as ins


router = APIRouter(prefix="/me/installment-plans", tags=["installments"])


class InstallmentItem(BaseModel):
    id: str
    sequence: int
    amount: float
    currency: str
    due_date: str | None
    status: str
    paid_at: str | None


class PlanItem(BaseModel):
    id: str
    booking_id: str
    total_amount: float
    currency: str
    n_installments: int
    status: str
    installments: list[InstallmentItem]


class PlanCreate(BaseModel):
    booking_id: str = Field(min_length=1, max_length=36)
    n_installments: int = Field(default=2, ge=2, le=3)


class PayResult(BaseModel):
    installment_id: str
    sequence: int
    status: str
    plan_completed: bool


@router.get("", response_model=list[PlanItem])
@limiter.limit("60/minute")
def list_plans(
    request: Request,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[PlanItem]:
    return [PlanItem(**p) for p in ins.list_plans(db, user_id=user.id)]


@router.post("", response_model=PlanItem, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_plan(
    request: Request,
    payload: PlanCreate,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PlanItem:
    plan, st = ins.create_plan(
        db, user_id=user.id, booking_id=payload.booking_id,
        n_installments=payload.n_installments,
    )
    if st == "bad_n":
        raise HTTPException(status_code=422, detail="n_installments must be 2 or 3")
    if st == "not_found":
        raise HTTPException(status_code=404, detail="Booking not found")
    if st == "already_paid":
        raise HTTPException(status_code=409, detail="Booking is already paid")
    # fetch fresh list to return the created/existing plan
    rows = ins.list_plans(db, user_id=user.id)
    for r in rows:
        if r["id"] == plan.id:
            return PlanItem(**r)
    raise HTTPException(status_code=500, detail="Plan created but not found")


@router.get("/{plan_id}", response_model=PlanItem)
@limiter.limit("60/minute")
def get_plan(
    request: Request,
    plan_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PlanItem:
    plan = ins.get_plan(db, user_id=user.id, plan_id=plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    rows = ins.list_plans(db, user_id=user.id)
    for r in rows:
        if r["id"] == plan_id:
            return PlanItem(**r)
    raise HTTPException(status_code=500, detail="Plan not found")


@router.post("/installments/{installment_id}/pay", response_model=PayResult)
@limiter.limit("30/minute")
def pay_installment(
    request: Request,
    installment_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PayResult:
    """Mark a single installment as paid (mock payment).

    Real payment integration is deferred to Phase 10.
    """
    inst, st = ins.mark_paid(db, user_id=user.id, installment_id=installment_id)
    if st == "not_found":
        raise HTTPException(status_code=404, detail="Installment not found")
    # check if plan completed
    plan = db.query(ins.InstallmentPlan).filter(ins.InstallmentPlan.id == inst.plan_id).one_or_none()
    plan_completed = bool(plan and plan.status == "completed")
    return PayResult(
        installment_id=inst.id,
        sequence=inst.sequence,
        status=inst.status,
        plan_completed=plan_completed,
    )


@router.delete("/{plan_id}")
@limiter.limit("30/minute")
def cancel_plan(
    request: Request,
    plan_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> dict:
    ok = ins.cancel_plan(db, user_id=user.id, plan_id=plan_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Plan not found or cannot be cancelled")
    return {"cancelled": True, "plan_id": plan_id}
