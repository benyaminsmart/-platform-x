"""End-to-end tests for notifications."""

from fastapi.testclient import TestClient

from app.models.tenant import Tenant
from app.services import notification_service

def _clear_notifications(db):
    """Remove any notifications created by auto-hooks."""
    from app.models.notification import Notification
    db.query(Notification).delete()
    db.commit()




def _register(client: TestClient, tenant: Tenant, email: str) -> dict:
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Pass1234",
            "first_name": "N",
            "last_name": "T",
        },
        headers={"X-Tenant-Slug": tenant.slug},
    )
    token = r.json()["access_token"]
    return {
        "X-Tenant-Slug": tenant.slug,
        "Authorization": f"Bearer {token}",
    }


def _register_clean(client, tenant, email, db):
    """Register and clear auto-hook notifications so tests start clean."""
    h = _register(client, tenant, email)
    _clear_notifications(db)
    return h


def test_list_empty(client: TestClient, sample_tenant: Tenant, db) -> None:
    h = _register_clean(client, sample_tenant, "n1@example.com", db)
    resp = client.get("/notifications", headers=h)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_unread_count_empty(client: TestClient, sample_tenant: Tenant, db) -> None:
    h = _register_clean(client, sample_tenant, "n2@example.com", db)
    resp = client.get("/notifications/unread-count", headers=h)
    assert resp.status_code == 200
    assert resp.json()["unread"] == 0


def test_create_and_list(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    h = _register_clean(client, sample_tenant, "n3@example.com", db)
    uid = client.get("/auth/me", headers=h).json()["id"]

    notification_service.create(
        db,
        tenant_id=sample_tenant.id,
        user_id=uid,
        channel="in_app",
        template="booking_confirmed",
        content="Your booking is confirmed",
        subject="Booking",
    )
    notification_service.create(
        db,
        tenant_id=sample_tenant.id,
        user_id=uid,
        channel="in_app",
        template="order_ready",
        content="Order ready",
    )

    resp = client.get("/notifications", headers=h)
    d = resp.json()
    assert d["total"] == 2
    assert len(d["items"]) == 2
    # Newest first
    assert d["items"][0]["template"] == "order_ready"


def test_mark_read_and_unread_count(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    h = _register_clean(client, sample_tenant, "n4@example.com", db)
    uid = client.get("/auth/me", headers=h).json()["id"]
    n = notification_service.create(
        db,
        tenant_id=sample_tenant.id,
        user_id=uid,
        channel="in_app",
        template="welcome",
        content="Welcome!",
    )

    assert client.get("/notifications/unread-count", headers=h).json()["unread"] == 1

    r = client.post(f"/notifications/{n.id}/read", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "read"
    assert r.json()["read_at"] is not None

    assert client.get("/notifications/unread-count", headers=h).json()["unread"] == 0


def test_mark_read_idempotent(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    h = _register_clean(client, sample_tenant, "n5@example.com", db)
    uid = client.get("/auth/me", headers=h).json()["id"]
    n = notification_service.create(
        db,
        tenant_id=sample_tenant.id,
        user_id=uid,
        channel="in_app",
        template="x",
        content="x",
    )
    r1 = client.post(f"/notifications/{n.id}/read", headers=h)
    r2 = client.post(f"/notifications/{n.id}/read", headers=h)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["read_at"] == r2.json()["read_at"]


def test_mark_read_unknown_404(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    h = _register_clean(client, sample_tenant, "n6@example.com", db)
    resp = client.post("/notifications/nope/read", headers=h)
    assert resp.status_code == 404


def test_filter_unread_only(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    h = _register_clean(client, sample_tenant, "n7@example.com", db)
    uid = client.get("/auth/me", headers=h).json()["id"]
    n1 = notification_service.create(
        db, tenant_id=sample_tenant.id, user_id=uid, channel="in_app",
        template="a", content="a",
    )
    notification_service.create(
        db, tenant_id=sample_tenant.id, user_id=uid, channel="in_app",
        template="b", content="b",
    )
    client.post(f"/notifications/{n1.id}/read", headers=h)

    resp = client.get("/notifications?unread_only=true", headers=h)
    assert resp.json()["total"] == 1


def test_tenant_isolation(client: TestClient, sample_tenant: Tenant, db) -> None:
    from app.models.tenant import Tenant as T

    other = T(slug="other", name="Other", tier="starter", status="active", config={})
    db.add(other)
    db.commit()

    h = _register_clean(client, sample_tenant, "n8@example.com", db)
    uid = client.get("/auth/me", headers=h).json()["id"]
    notification_service.create(
        db, tenant_id=sample_tenant.id, user_id=uid, channel="in_app",
        template="x", content="x",
    )

    # Users are platform-wide: same token works on other tenant, sees that tenant's data
    resp = client.get("/notifications", headers={"X-Tenant-Slug": "other", "Authorization": h["Authorization"]})
    assert resp.status_code == 200
    # But this tenant has no notifications for this user yet
    assert resp.json()["total"] == 0
