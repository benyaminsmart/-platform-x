"""Tests for category pages."""

from fastapi.testclient import TestClient

from app.models.tenant import Tenant


def _make_tenant(db, slug: str, name: str, cat_type: str) -> Tenant:
    t = Tenant(
        slug=slug, name=name, tier="starter", status="active",
        config={"type": cat_type, "tagline": f"Test {cat_type}"},
    )
    db.add(t)
    db.commit()
    return t


def test_hotels_page_loads(client: TestClient, db) -> None:
    _make_tenant(db, "hotel-1", "Hotel One", "hotel")
    resp = client.get("/hotels")
    assert resp.status_code == 200
    assert "Hotel One" in resp.text
    assert "🏨" in resp.text


def test_restaurants_page_loads(client: TestClient, db) -> None:
    _make_tenant(db, "rest-1", "Rest One", "restaurant")
    resp = client.get("/restaurants")
    assert resp.status_code == 200
    assert "Rest One" in resp.text


def test_travel_page_shows_agencies(client: TestClient, db) -> None:
    _make_tenant(db, "ag-1", "Agency One", "travel_agency")
    resp = client.get("/travel")
    assert resp.status_code == 200
    assert "Agency One" in resp.text


def test_entertainment_page_loads(client: TestClient, db) -> None:
    _make_tenant(db, "ent-1", "Fun Park", "entertainment")
    resp = client.get("/entertainment")
    assert resp.status_code == 200
    assert "Fun Park" in resp.text


def test_empty_category_shows_empty_state(client: TestClient) -> None:
    resp = client.get("/hotels")
    assert resp.status_code == 200
    assert "No hotels yet" in resp.text


def test_category_not_treated_as_tenant(client: TestClient) -> None:
    """GET /hotels/ (trailing slash) should 404, not be a tenant."""
    resp = client.get("/hotels/")
    assert resp.status_code == 404


def test_category_shows_only_matching_types(client: TestClient, db) -> None:
    _make_tenant(db, "h", "A Hotel", "hotel")
    _make_tenant(db, "r", "A Restaurant", "restaurant")
    resp = client.get("/hotels")
    assert "A Hotel" in resp.text
    assert "A Restaurant" not in resp.text
