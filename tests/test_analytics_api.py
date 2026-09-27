"""End-to-end tests for analytics."""

from fastapi.testclient import TestClient

from app.models.tenant import Tenant


def test_track_event_public(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.post(
        "/analytics/events",
        json={"event_type": "page_view", "metadata": {"path": "/"}},
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert resp.status_code == 201, resp.text
    d = resp.json()
    assert d["event_type"] == "page_view"
    assert d["metadata_json"]["path"] == "/"


def test_track_requires_tenant(client: TestClient) -> None:
    # No X-Tenant-Slug → falls back to default 'demo' which doesn't exist → 404
    resp = client.post("/analytics/events", json={"event_type": "x"})
    assert resp.status_code == 404


def test_track_invalid_event_422(client: TestClient, sample_tenant: Tenant) -> None:
    resp = client.post(
        "/analytics/events",
        json={"event_type": ""},
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert resp.status_code == 422


def test_summary_requires_admin(
    client: TestClient, sample_tenant: Tenant
) -> None:
    resp = client.get(
        "/analytics/summary", headers={"X-Tenant-Slug": sample_tenant.slug}
    )
    assert resp.status_code == 401


def test_summary_with_admin(
    client: TestClient, sample_tenant: Tenant, admin_client
) -> None:
    # Create some events
    h = {"X-Tenant-Slug": sample_tenant.slug}
    for et in ["page_view", "page_view", "booking_started"]:
        client.post("/analytics/events", json={"event_type": et}, headers=h)

    _, auth = admin_client
    resp = client.get("/analytics/summary", headers={**h, **auth})
    assert resp.status_code == 200
    d = resp.json()
    assert d["total_events"] == 3
    top = {e["event_type"]: e["count"] for e in d["top_events"]}
    assert top["page_view"] == 2
    assert top["booking_started"] == 1


def test_tenant_isolation_summary(
    client: TestClient, sample_tenant: Tenant, admin_client, db
) -> None:
    from app.models.tenant import Tenant as T

    other = T(slug="other", name="Other", tier="starter", status="active", config={})
    db.add(other)
    db.commit()

    h_a = {"X-Tenant-Slug": sample_tenant.slug}
    h_b = {"X-Tenant-Slug": "other"}
    client.post("/analytics/events", json={"event_type": "a"}, headers=h_a)
    client.post("/analytics/events", json={"event_type": "b"}, headers=h_b)

    _, auth = admin_client
    resp_a = client.get("/analytics/summary", headers={**h_a, **auth})
    resp_b = client.get("/analytics/summary", headers={**h_b, **auth})
    assert resp_a.json()["total_events"] == 1
    assert resp_b.json()["total_events"] == 1
