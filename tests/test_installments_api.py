"""Tests for Installment API (Phase 57, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User


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


def _booking(db, t, u, amount=1000, payment_status="pending"):
    ci = date.today() + timedelta(days=30)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci,
                check_out=ci + timedelta(days=2), guests=1,
                amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status="pending", payment_status=payment_status)
    db.add(b); db.commit(); db.refresh(b)
    return b


def _login(client, slug, email):
    r = client.post("/auth/login", json={"email": email, "password": "Pass1234"},
                    headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_create_requires_auth(client: TestClient) -> None:
    r = client.post("/me/installment-plans", json={"booking_id": "x"})
    assert r.status_code == 401


def test_create_and_list(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ins-api-1")
    u = _user(db, t)
    b = _booking(db, t, u, amount=1000)
    token = _login(client, t.slug, u.email)
    h = {"Authorization": f"Bearer {token}"}

    r = client.post("/me/installment-plans",
                    json={"booking_id": b.id, "n_installments": 2}, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["n_installments"] == 2
    assert len(body["installments"]) == 2
    assert body["installments"][0]["amount"] == 500.0

    r = client.get("/me/installment-plans", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_create_booking_not_found(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ins-api-nf")
    u = _user(db, t, "nf@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/me/installment-plans",
                    json={"booking_id": "does-not-exist"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_pay_installment(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ins-api-pay")
    u = _user(db, t, "pay@x.com")
    b = _booking(db, t, u, amount=1000)
    token = _login(client, t.slug, u.email)
    h = {"Authorization": f"Bearer {token}"}

    r = client.post("/me/installment-plans",
                    json={"booking_id": b.id, "n_installments": 2}, headers=h)
    plan = r.json()
    inst1 = plan["installments"][0]["id"]
    inst2 = plan["installments"][1]["id"]

    r = client.post(f"/me/installment-plans/installments/{inst1}/pay", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "paid"
    assert r.json()["plan_completed"] is False

    r = client.post(f"/me/installment-plans/installments/{inst2}/pay", headers=h)
    assert r.status_code == 200
    assert r.json()["plan_completed"] is True


def test_cancel_plan(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ins-api-cancel")
    u = _user(db, t, "cancel@x.com")
    b = _booking(db, t, u)
    token = _login(client, t.slug, u.email)
    h = {"Authorization": f"Bearer {token}"}

    r = client.post("/me/installment-plans",
                    json={"booking_id": b.id}, headers=h)
    plan_id = r.json()["id"]

    r = client.delete(f"/me/installment-plans/{plan_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["cancelled"] is True


def test_cross_user_isolation(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ins-api-iso")
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    b = _booking(db, t, u1)
    tok1 = _login(client, t.slug, u1.email)
    tok2 = _login(client, t.slug, u2.email)

    r = client.post("/me/installment-plans",
                    json={"booking_id": b.id},
                    headers={"Authorization": f"Bearer {tok1}"})
    plan_id = r.json()["id"]

    r = client.get(f"/me/installment-plans/{plan_id}",
                   headers={"Authorization": f"Bearer {tok2}"})
    assert r.status_code == 404

    r = client.delete(f"/me/installment-plans/{plan_id}",
                      headers={"Authorization": f"Bearer {tok2}"})
    assert r.status_code == 404


def test_create_bad_n(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ins-api-badn")
    u = _user(db, t, "badn@x.com")
    b = _booking(db, t, u)
    token = _login(client, t.slug, u.email)
    r = client.post("/me/installment-plans",
                    json={"booking_id": b.id, "n_installments": 5},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_create_already_paid(client: TestClient, db: Session) -> None:
    t = _tenant(db, "ins-api-paid")
    u = _user(db, t, "paid@x.com")
    b = _booking(db, t, u, payment_status="paid")
    token = _login(client, t.slug, u.email)
    r = client.post("/me/installment-plans",
                    json={"booking_id": b.id},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 409
