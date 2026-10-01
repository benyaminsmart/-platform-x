"""Tests for Installment service (Phase 57, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.installment import Installment, InstallmentPlan
from app.models.tenant import Tenant
from app.models.user import User
from app.services import installment_service as ins


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, amount=1000, days=30, payment_status="pending"):
    ci = date.today() + timedelta(days=days)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci,
                check_out=ci + timedelta(days=2), guests=1,
                amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status="pending", payment_status=payment_status)
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_create_bad_n(db):
    t = _tenant(db, "ins-badn")
    u = _user(db, t)
    b = _booking(db, t, u)
    plan, st = ins.create_plan(db, user_id=u.id, booking_id=b.id, n_installments=5)
    assert st == "bad_n"
    assert plan is None


def test_create_not_found(db):
    t = _tenant(db, "ins-nf")
    u = _user(db, t, "nf@x.com")
    plan, st = ins.create_plan(db, user_id=u.id, booking_id="does-not-exist")
    assert st == "not_found"


def test_create_already_paid(db):
    t = _tenant(db, "ins-paid")
    u = _user(db, t, "paid@x.com")
    b = _booking(db, t, u, payment_status="paid")
    plan, st = ins.create_plan(db, user_id=u.id, booking_id=b.id)
    assert st == "already_paid"


def test_create_2_installments(db):
    t = _tenant(db, "ins-2")
    u = _user(db, t, "two@x.com")
    b = _booking(db, t, u, amount=1000)
    plan, st = ins.create_plan(db, user_id=u.id, booking_id=b.id, n_installments=2)
    assert st == "ok"
    assert plan.status == "active"
    items = db.query(Installment).filter(Installment.plan_id == plan.id).order_by(Installment.sequence).all()
    assert len(items) == 2
    # First = 50% down payment
    assert items[0].amount == Decimal("500.00")
    assert items[1].amount == Decimal("500.00")
    total = sum(i.amount for i in items)
    assert total == Decimal("1000.00")


def test_create_3_installments(db):
    t = _tenant(db, "ins-3")
    u = _user(db, t, "three@x.com")
    b = _booking(db, t, u, amount=1000)
    plan, st = ins.create_plan(db, user_id=u.id, booking_id=b.id, n_installments=3)
    assert st == "ok"
    items = db.query(Installment).filter(Installment.plan_id == plan.id).order_by(Installment.sequence).all()
    assert len(items) == 3
    # First = 40% = 400, remaining 600/2 = 300 each
    assert items[0].amount == Decimal("400.00")
    assert items[1].amount == Decimal("300.00")
    assert items[2].amount == Decimal("300.00")
    total = sum(i.amount for i in items)
    assert total == Decimal("1000.00")


def test_rounding_adjusts_last_installment(db):
    t = _tenant(db, "ins-round")
    u = _user(db, t, "round@x.com")
    b = _booking(db, t, u, amount=100)  # 100/3 = 33.33...
    plan, st = ins.create_plan(db, user_id=u.id, booking_id=b.id, n_installments=3)
    items = db.query(Installment).filter(Installment.plan_id == plan.id).order_by(Installment.sequence).all()
    total = sum(i.amount for i in items)
    assert total == Decimal("100.00")


def test_create_existing_plan(db):
    t = _tenant(db, "ins-exists")
    u = _user(db, t, "exists@x.com")
    b = _booking(db, t, u)
    p1, st = ins.create_plan(db, user_id=u.id, booking_id=b.id)
    assert st == "ok"
    p2, st2 = ins.create_plan(db, user_id=u.id, booking_id=b.id)
    assert st2 == "exists"
    assert p2.id == p1.id


def test_mark_paid_completes_plan(db):
    t = _tenant(db, "ins-complete")
    u = _user(db, t, "complete@x.com")
    b = _booking(db, t, u, amount=600)
    plan, _ = ins.create_plan(db, user_id=u.id, booking_id=b.id, n_installments=2)
    items = db.query(Installment).filter(Installment.plan_id == plan.id).order_by(Installment.sequence).all()
    inst1, st1 = ins.mark_paid(db, user_id=u.id, installment_id=items[0].id)
    assert st1 == "ok"
    assert plan.status == "active"  # not yet complete
    inst2, st2 = ins.mark_paid(db, user_id=u.id, installment_id=items[1].id)
    assert st2 == "ok"
    db.refresh(plan)
    assert plan.status == "completed"
    assert plan.completed_at is not None


def test_mark_paid_twice(db):
    t = _tenant(db, "ins-twice")
    u = _user(db, t, "twice@x.com")
    b = _booking(db, t, u)
    plan, _ = ins.create_plan(db, user_id=u.id, booking_id=b.id)
    items = db.query(Installment).filter(Installment.plan_id == plan.id).order_by(Installment.sequence).all()
    ins.mark_paid(db, user_id=u.id, installment_id=items[0].id)
    inst, st = ins.mark_paid(db, user_id=u.id, installment_id=items[0].id)
    assert st == "already_paid"


def test_list_plans(db):
    t = _tenant(db, "ins-list")
    u = _user(db, t, "list@x.com")
    b = _booking(db, t, u)
    ins.create_plan(db, user_id=u.id, booking_id=b.id)
    rows = ins.list_plans(db, user_id=u.id)
    assert len(rows) == 1
    assert rows[0]["n_installments"] == 2
    assert len(rows[0]["installments"]) == 2


def test_next_due(db):
    t = _tenant(db, "ins-next")
    u = _user(db, t, "next@x.com")
    b = _booking(db, t, u)
    plan, _ = ins.create_plan(db, user_id=u.id, booking_id=b.id)
    due = ins.next_due(db, plan_id=plan.id)
    assert due is not None
    assert due.sequence == 1


def test_cancel_plan(db):
    t = _tenant(db, "ins-cancel")
    u = _user(db, t, "cancel@x.com")
    b = _booking(db, t, u)
    plan, _ = ins.create_plan(db, user_id=u.id, booking_id=b.id)
    assert ins.cancel_plan(db, user_id=u.id, plan_id=plan.id) is True
    db.refresh(plan)
    assert plan.status == "cancelled"
    items = db.query(Installment).filter(Installment.plan_id == plan.id).all()
    for i in items:
        assert i.status == "cancelled"


def test_cross_user_isolation(db):
    t = _tenant(db, "ins-iso")
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    b = _booking(db, t, u1)
    plan, _ = ins.create_plan(db, user_id=u1.id, booking_id=b.id)
    assert ins.get_plan(db, user_id=u2.id, plan_id=plan.id) is None
    assert ins.cancel_plan(db, user_id=u2.id, plan_id=plan.id) is False
