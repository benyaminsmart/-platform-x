"""Tests for the Business Owner Panel API (Phase 20).

Covers auth, dashboard, services CRUD, bookings inbox, customers,
and role-based staff management.
"""

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User


# ---------- Helpers ----------


def _make_business_user(
    db,
    tenant: Tenant,
    *,
    email: str = "owner@biz.test",
    password: str = "OwnerPass123",
    role: str = "owner",
    status: str = "active",
) -> User:
    u = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(password),
        first_name="Owner",
        last_name="One",
        business_role=role,
        status=status,
        referral_code=email[:10].upper(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client: TestClient, slug: str, email: str, password: str):
    return client.post(
        "/business/api/auth/login",
        json={"email": email, "password": password},
        headers={"X-Tenant-Slug": slug},
    )


def _auth_headers(token: str, slug: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Slug": slug}


# ---------- Auth ----------


def test_business_login_success(client: TestClient, sample_tenant: Tenant, db) -> None:
    _make_business_user(db, sample_tenant)
    r = _login(client, sample_tenant.slug, "owner@biz.test", "OwnerPass123")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


def test_business_login_wrong_password(client: TestClient, sample_tenant: Tenant, db) -> None:
    _make_business_user(db, sample_tenant)
    r = _login(client, sample_tenant.slug, "owner@biz.test", "WrongPass999")
    assert r.status_code == 401


def test_business_login_missing_slug(client: TestClient, sample_tenant: Tenant, db) -> None:
    _make_business_user(db, sample_tenant)
    r = client.post(
        "/business/api/auth/login",
        json={"email": "owner@biz.test", "password": "OwnerPass123"},
    )
    assert r.status_code == 400


def test_business_login_unknown_tenant(client: TestClient, db) -> None:
    r = client.post(
        "/business/api/auth/login",
        json={"email": "x@x.com", "password": "whatever1"},
        headers={"X-Tenant-Slug": "does-not-exist"},
    )
    assert r.status_code == 404


def test_business_login_regular_user_forbidden(client: TestClient, sample_tenant: Tenant, db) -> None:
    # user with no business_role
    u = User(
        tenant_id=sample_tenant.id,
        email="guest@biz.test",
        password_hash=hash_password("GuestPass123"),
        first_name="G",
        last_name="U",
        business_role=None,
        status="active",
        referral_code="GUESTCODE1",
    )
    db.add(u)
    db.commit()
    r = _login(client, sample_tenant.slug, "guest@biz.test", "GuestPass123")
    assert r.status_code == 403


# ---------- /me ----------


def test_business_me_success(client: TestClient, sample_tenant: Tenant, db) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug, "owner@biz.test", "OwnerPass123").json()["access_token"]
    r = client.get("/business/api/me", headers=_auth_headers(token, sample_tenant.slug))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "owner@biz.test"
    assert body["business_role"] == "owner"
    assert body["tenant_slug"] == sample_tenant.slug


def test_business_me_no_token(client: TestClient, sample_tenant: Tenant) -> None:
    r = client.get("/business/api/me", headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 401


def test_business_me_regular_user_forbidden(client: TestClient, sample_tenant: Tenant, db) -> None:
    # regular guest token (via /auth/register)
    reg = client.post(
        "/auth/register",
        json={
            "email": "guest@x.com",
            "password": "GuestPass123",
            "first_name": "G",
            "last_name": "U",
        },
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    token = reg.json()["access_token"]
    r = client.get("/business/api/me", headers=_auth_headers(token, sample_tenant.slug))
    assert r.status_code == 403


# ---------- /dashboard ----------


def test_business_dashboard_stats(client: TestClient, sample_tenant: Tenant, db) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug, "owner@biz.test", "OwnerPass123").json()["access_token"]
    r = client.get("/business/api/dashboard", headers=_auth_headers(token, sample_tenant.slug))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant"]["slug"] == sample_tenant.slug
    stats = body["stats"]
    assert stats["total_bookings"] == 0
    assert stats["confirmed_bookings"] == 0
    assert stats["active_services"] == 0
    assert stats["revenue_aed"] == 0.0


# ---------- Services CRUD ----------


def test_business_services_crud(client: TestClient, sample_tenant: Tenant, db) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug, "owner@biz.test", "OwnerPass123").json()["access_token"]
    h = _auth_headers(token, sample_tenant.slug)

    # list initially empty
    r = client.get("/business/api/services", headers=h)
    assert r.status_code == 200
    assert r.json() == []

    # create
    r = client.post(
        "/business/api/services",
        json={
            "type": "room",
            "name": "Deluxe Suite",
            "description": "Sea view",
            "price": 899.0,
            "currency": "AED",
            "capacity": 2,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    sid = r.json()["id"]

    # list has one
    r = client.get("/business/api/services", headers=h)
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Deluxe Suite"

    # update
    r = client.patch(
        f"/business/api/services/{sid}",
        json={"price": 999.0, "name": "Deluxe Suite Plus"},
        headers=h,
    )
    assert r.status_code == 200

    r = client.get("/business/api/services", headers=h)
    assert r.json()[0]["name"] == "Deluxe Suite Plus"
    assert float(r.json()[0]["price"]) == 999.0

    # soft-delete
    r = client.delete(f"/business/api/services/{sid}", headers=h)
    assert r.status_code == 200

    r = client.get("/business/api/services", headers=h)
    assert r.json()[0]["status"] == "inactive"


def test_business_services_cross_tenant_isolation(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    # tenant A
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug, "owner@biz.test", "OwnerPass123").json()["access_token"]
    h = _auth_headers(token, sample_tenant.slug)
    r = client.post(
        "/business/api/services",
        json={"type": "room", "name": "A Room", "price": 100.0},
        headers=h,
    )
    sid = r.json()["id"]

    # tenant B
    tb = Tenant(slug="other", name="Other Biz", tier="starter", status="active", config={})
    db.add(tb)
    db.commit()
    db.refresh(tb)
    _make_business_user(db, tb, email="owner@other.test")
    token_b = _login(client, tb.slug, "owner@other.test", "OwnerPass123").json()["access_token"]
    hb = _auth_headers(token_b, tb.slug)

    # B cannot see A's service
    r = client.get("/business/api/services", headers=hb)
    assert r.json() == []

    # B cannot update A's service
    r = client.patch(
        f"/business/api/services/{sid}",
        json={"name": "Hacked"},
        headers=hb,
    )
    assert r.status_code == 404

    # B cannot delete A's service
    r = client.delete(f"/business/api/services/{sid}", headers=hb)
    assert r.status_code == 404


# ---------- Bookings ----------


def test_business_bookings_inbox_and_status_update(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug, "owner@biz.test", "OwnerPass123").json()["access_token"]
    h = _auth_headers(token, sample_tenant.slug)

    # create a service
    r = client.post(
        "/business/api/services",
        json={"type": "room", "name": "Std Room", "price": 500.0},
        headers=h,
    )
    sid = r.json()["id"]

    # register a guest + book
    reg = client.post(
        "/auth/register",
        json={
            "email": "guest@x.com",
            "password": "GuestPass123",
            "first_name": "G",
            "last_name": "U",
        },
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    guest_h = {
        "X-Tenant-Slug": sample_tenant.slug,
        "Authorization": f"Bearer {reg.json()['access_token']}",
    }
    bk = client.post(
        "/bookings",
        json={
            "booking_type": "room",
            "service_id": sid,
            "service_name": "Std Room",
            "check_in": "2026-10-10",
            "check_out": "2026-10-12",
            "guests": 2,
            "amount": "500.00",
        },
        headers=guest_h,
    )
    assert bk.status_code == 201
    bid = bk.json()["id"]

    # inbox
    r = client.get("/business/api/bookings", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["service_name"] == "Std Room"

    # status filter
    r = client.get("/business/api/bookings?status_filter=confirmed", headers=h)
    assert r.json()["total"] == 0

    # update status
    r = client.patch(
        f"/business/api/bookings/{bid}/status",
        json={"status": "confirmed"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    # invalid status
    r = client.patch(
        f"/business/api/bookings/{bid}/status",
        json={"status": "bogus"},
        headers=h,
    )
    assert r.status_code == 400


# ---------- Customers ----------


def test_business_customers_list(client: TestClient, sample_tenant: Tenant, db) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug, "owner@biz.test", "OwnerPass123").json()["access_token"]
    h = _auth_headers(token, sample_tenant.slug)

    # no customers yet
    r = client.get("/business/api/customers", headers=h)
    assert r.status_code == 200
    assert r.json() == []

    # register guest + book once
    reg = client.post(
        "/auth/register",
        json={
            "email": "cust@x.com",
            "password": "GuestPass123",
            "first_name": "Cust",
            "last_name": "Omer",
        },
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    guest_h = {
        "X-Tenant-Slug": sample_tenant.slug,
        "Authorization": f"Bearer {reg.json()['access_token']}",
    }
    client.post(
        "/bookings",
        json={
            "booking_type": "room",
            "service_name": "Any",
            "check_in": "2026-10-10",
            "check_out": "2026-10-11",
            "guests": 1,
            "amount": "100.00",
        },
        headers=guest_h,
    )

    r = client.get("/business/api/customers", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["email"] == "cust@x.com"
    assert r.json()[0]["bookings_count"] == 1


# ---------- Staff ----------


def test_business_staff_create_and_delete(client: TestClient, sample_tenant: Tenant, db) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug, "owner@biz.test", "OwnerPass123").json()["access_token"]
    h = _auth_headers(token, sample_tenant.slug)

    # list contains only the owner
    r = client.get("/business/api/staff", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["business_role"] == "owner"

    # create a manager
    r = client.post(
        "/business/api/staff",
        json={
            "email": "mgr@biz.test",
            "password": "ManagerPass1",
            "first_name": "M",
            "last_name": "Gr",
            "business_role": "manager",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    mid = r.json()["id"]

    r = client.get("/business/api/staff", headers=h)
    assert len(r.json()) == 2

    # cannot deactivate self
    me = client.get("/business/api/me", headers=h).json()
    r = client.delete(f"/business/api/staff/{me['id']}", headers=h)
    assert r.status_code == 400

    # deactivate the manager
    r = client.delete(f"/business/api/staff/{mid}", headers=h)
    assert r.status_code == 200


def test_business_staff_validation_errors(client: TestClient, sample_tenant: Tenant, db) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug, "owner@biz.test", "OwnerPass123").json()["access_token"]
    h = _auth_headers(token, sample_tenant.slug)

    # missing fields
    r = client.post("/business/api/staff", json={"email": "a@b.com"}, headers=h)
    assert r.status_code == 400

    # invalid role
    r = client.post(
        "/business/api/staff",
        json={
            "email": "x@b.com",
            "password": "Pass1234",
            "first_name": "X",
            "last_name": "Y",
            "business_role": "superboss",
        },
        headers=h,
    )
    assert r.status_code == 400

    # short password
    r = client.post(
        "/business/api/staff",
        json={
            "email": "x@b.com",
            "password": "short",
            "first_name": "X",
            "last_name": "Y",
            "business_role": "staff",
        },
        headers=h,
    )
    assert r.status_code == 400

    # duplicate email
    r = client.post(
        "/business/api/staff",
        json={
            "email": "dup@b.com",
            "password": "Pass1234",
            "first_name": "D",
            "last_name": "Up",
            "business_role": "staff",
        },
        headers=h,
    )
    assert r.status_code == 201
    r = client.post(
        "/business/api/staff",
        json={
            "email": "dup@b.com",
            "password": "Pass1234",
            "first_name": "D",
            "last_name": "Up",
            "business_role": "staff",
        },
        headers=h,
    )
    assert r.status_code == 409


def test_business_staff_permission_staff_cannot_create(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    # create owner + a staff user
    _make_business_user(db, sample_tenant, email="owner@biz.test", role="owner")
    _make_business_user(db, sample_tenant, email="staff@biz.test", role="staff")

    token = _login(client, sample_tenant.slug, "staff@biz.test", "OwnerPass123").json()["access_token"]
    h = _auth_headers(token, sample_tenant.slug)

    # staff cannot create
    r = client.post(
        "/business/api/staff",
        json={
            "email": "new@biz.test",
            "password": "Pass1234",
            "first_name": "N",
            "last_name": "Ew",
            "business_role": "staff",
        },
        headers=h,
    )
    assert r.status_code == 403

    # staff cannot delete
    owner = db.query(User).filter(User.email == "owner@biz.test").one()
    r = client.delete(f"/business/api/staff/{owner.id}", headers=h)
    assert r.status_code == 403


def test_business_staff_delete_cross_tenant_blocked(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    # tenant A owner
    _make_business_user(db, sample_tenant, email="owner@a.test")
    # tenant B owner + staff
    tb = Tenant(slug="other-b", name="Other B", tier="starter", status="active", config={})
    db.add(tb)
    db.commit()
    db.refresh(tb)
    _make_business_user(db, tb, email="owner@b.test")
    other_staff = _make_business_user(db, tb, email="staff@b.test", role="staff")

    token_a = _login(client, sample_tenant.slug, "owner@a.test", "OwnerPass123").json()["access_token"]
    ha = _auth_headers(token_a, sample_tenant.slug)

    # A tries to delete B's staff → 404
    r = client.delete(f"/business/api/staff/{other_staff.id}", headers=ha)
    assert r.status_code == 404
