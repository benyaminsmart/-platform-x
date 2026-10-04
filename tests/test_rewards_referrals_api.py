"""End-to-end tests for rewards and referrals."""

from fastapi.testclient import TestClient

from app.models.tenant import Tenant
from app.services import reward_service


def _register(client: TestClient, tenant: Tenant, email: str) -> dict:
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Pass1234",
            "first_name": "U",
            "last_name": "X",
        },
        headers={"X-Tenant-Slug": tenant.slug},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return {
        "X-Tenant-Slug": tenant.slug,
        "Authorization": f"Bearer {token}",
        "X-Email": email,
    }


# --- Rewards ---


def test_rewards_summary_initial(client: TestClient, sample_tenant: Tenant) -> None:
    h = _register(client, sample_tenant, "rw1@example.com")
    resp = client.get("/rewards/me", headers=h)
    assert resp.status_code == 200
    d = resp.json()
    assert d["points"] == 0
    assert d["tier"] == "welcome"
    assert d["next_tier"] == "silver"
    assert d["points_to_next_tier"] == 500


def test_rewards_history_empty(client: TestClient, sample_tenant: Tenant) -> None:
    h = _register(client, sample_tenant, "rw2@example.com")
    resp = client.get("/rewards/history", headers=h)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_rewards_earn_and_tier_progress(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    h = _register(client, sample_tenant, "rw3@example.com")
    me = client.get("/auth/me", headers=h).json()
    uid = me["id"]

    # Directly award points (no API for earn path; internal service)
    reward_service.add_points(
        db, tenant_id=sample_tenant.id, user_id=uid, points=600, reward_type="earn"
    )

    # New TestClient call → same DB session via override
    resp = client.get("/rewards/me", headers=h)
    d = resp.json()
    assert d["points"] == 600
    assert d["tier"] == "silver"
    assert d["next_tier"] == "gold"

    hist = client.get("/rewards/history", headers=h)
    assert hist.json()["total"] == 1


def test_redeem_insufficient_points(
    client: TestClient, sample_tenant: Tenant, db
) -> None:
    h = _register(client, sample_tenant, "rw4@example.com")
    uid = client.get("/auth/me", headers=h).json()["id"]
    # earn small then try to redeem big
    reward = reward_service.add_points(
        db, tenant_id=sample_tenant.id, user_id=uid, points=10, reward_type="earn"
    )
    # Force user points to 0 to trigger failure
    from app.models.user import User
    u = db.query(User).filter(User.id == uid).one()
    u.points = 0
    db.commit()

    resp = client.post("/rewards/redeem", json={"reward_id": reward.id}, headers=h)
    assert resp.status_code == 400


def test_redeem_success(client: TestClient, sample_tenant: Tenant, db) -> None:
    h = _register(client, sample_tenant, "rw5@example.com")
    uid = client.get("/auth/me", headers=h).json()["id"]
    reward = reward_service.add_points(
        db, tenant_id=sample_tenant.id, user_id=uid, points=200, reward_type="earn"
    )

    resp = client.post("/rewards/redeem", json={"reward_id": reward.id}, headers=h)
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d["reward_type"] == "redeem"
    assert d["points"] == -200

    # Points now zero
    me = client.get("/rewards/me", headers=h).json()
    assert me["points"] == 0


def test_redeem_unknown_reward_404(client: TestClient, sample_tenant: Tenant) -> None:
    h = _register(client, sample_tenant, "rw6@example.com")
    resp = client.post("/rewards/redeem", json={"reward_id": "nope"}, headers=h)
    assert resp.status_code == 404


# --- Referrals ---


def test_referrals_me_empty(client: TestClient, sample_tenant: Tenant) -> None:
    h = _register(client, sample_tenant, "ref1@example.com")
    resp = client.get("/referrals/me", headers=h)
    assert resp.status_code == 200
    d = resp.json()
    assert d["referral_code"]
    assert d["referred_count"] == 0
    assert d["completed_count"] == 0


def test_apply_own_code_rejected(client: TestClient, sample_tenant: Tenant) -> None:
    h = _register(client, sample_tenant, "ref2@example.com")
    me = client.get("/referrals/me", headers=h).json()
    resp = client.post(
        "/referrals/apply", json={"referral_code": me["referral_code"]}, headers=h
    )
    assert resp.status_code == 400


def test_apply_unknown_code_rejected(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _register(client, sample_tenant, "ref3@example.com")
    resp = client.post(
        "/referrals/apply", json={"referral_code": "NOPE_CODE"}, headers=h
    )
    assert resp.status_code == 400


def test_apply_registers_relationship_no_immediate_points(
    client: TestClient, sample_tenant: Tenant
) -> None:
    """Phase 77: apply no longer awards points immediately.

    Rewards fire only after the referred user completes a qualifying
    transaction (>= AED 300, paid). This test asserts the registered
    state, not points.
    """
    h_a = _register(client, sample_tenant, "referrer@example.com")
    code_a = client.get("/referrals/me", headers=h_a).json()["referral_code"]

    h_b = _register(client, sample_tenant, "referred@example.com")
    resp = client.post(
        "/referrals/apply", json={"referral_code": code_a}, headers=h_b
    )
    assert resp.status_code == 201, resp.text
    rel = resp.json()
    assert rel["status"] == "REGISTERED"

    refs = client.get("/referrals/me", headers=h_a).json()
    assert refs["referred_count"] == 1
    assert refs["completed_count"] == 0
    assert refs["pending_count"] == 1


def test_apply_twice_is_idempotent(client: TestClient, sample_tenant: Tenant) -> None:
    """Phase 77: applying the same code twice returns the same row."""
    h_a = _register(client, sample_tenant, "referrer2@example.com")
    code_a = client.get("/referrals/me", headers=h_a).json()["referral_code"]
    h_b = _register(client, sample_tenant, "referred2@example.com")
    r1 = client.post("/referrals/apply", json={"referral_code": code_a}, headers=h_b)
    r2 = client.post("/referrals/apply", json={"referral_code": code_a}, headers=h_b)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]



# --- reward_service tier unit tests ---


def test_tier_for_points() -> None:
    assert reward_service.tier_for_points(0) == "welcome"
    assert reward_service.tier_for_points(499) == "welcome"
    assert reward_service.tier_for_points(500) == "silver"
    assert reward_service.tier_for_points(2000) == "gold"
    assert reward_service.tier_for_points(5000) == "platinum"
    assert reward_service.tier_for_points(20000) == "royal"
