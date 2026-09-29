"""Tests for API Key service + deps (Phase 14, Step 2)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.api_key import APIKey
from app.models.tenant import Tenant
from app.services import api_key_service


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "apikey") -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


# ---------- generate_key ----------


def test_generate_key_shape() -> None:
    k = api_key_service.generate_key()
    assert k["plaintext"].startswith("pk_live_")
    assert k["prefix"].startswith("pk_live_")
    assert len(k["prefix"]) == len("pk_live_") + 8
    assert len(k["hashed"]) == 64  # sha256 hex
    # Two keys are distinct
    k2 = api_key_service.generate_key()
    assert k["plaintext"] != k2["plaintext"]


# ---------- validate_scopes ----------


def test_validate_scopes_ok() -> None:
    assert api_key_service.validate_scopes(["read:services"]) == ["read:services"]


def test_validate_scopes_empty_raises() -> None:
    with pytest.raises(ValueError):
        api_key_service.validate_scopes([])


def test_validate_scopes_unknown_raises() -> None:
    with pytest.raises(ValueError):
        api_key_service.validate_scopes(["read:nothing"])


# ---------- create / list / revoke ----------


def test_create_key_returns_plaintext_once(db: Session) -> None:
    t = _tenant(db)
    row, plaintext = api_key_service.create_key(
        db, tenant=t, name="Test key", scopes=["read:services"],
    )
    assert plaintext.startswith("pk_live_")
    assert row.prefix
    # Stored hash != plaintext
    assert row.hashed_key != plaintext
    # Serialized dict must NOT contain hashed_key
    s = api_key_service.serialize_key(row)
    assert "hashed_key" not in s
    assert s["name"] == "Test key"


def test_create_key_empty_name_raises(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        api_key_service.create_key(db, tenant=t, name="  ", scopes=["read:services"])


def test_list_keys_only_own_tenant(db: Session) -> None:
    t1 = _tenant(db, "k1")
    t2 = _tenant(db, "k2")
    api_key_service.create_key(db, tenant=t1, name="A", scopes=["read:services"])
    api_key_service.create_key(db, tenant=t2, name="B", scopes=["read:services"])
    rows = api_key_service.list_keys(db, t1)
    assert len(rows) == 1
    assert rows[0].name == "A"


def test_revoke_key(db: Session) -> None:
    t = _tenant(db)
    row, _ = api_key_service.create_key(db, tenant=t, name="X", scopes=["read:services"])
    updated = api_key_service.revoke_key(db, t, row.id)
    assert updated is not None
    assert updated.active is False


def test_revoke_wrong_tenant_returns_none(db: Session) -> None:
    t1 = _tenant(db, "r1")
    t2 = _tenant(db, "r2")
    row, _ = api_key_service.create_key(db, tenant=t1, name="X", scopes=["read:services"])
    assert api_key_service.revoke_key(db, t2, row.id) is None


# ---------- authenticate ----------


def test_authenticate_valid(db: Session) -> None:
    t = _tenant(db)
    row, plaintext = api_key_service.create_key(db, tenant=t, name="X", scopes=["read:services"])
    found = api_key_service.authenticate(db, plaintext)
    assert found is not None
    assert found.id == row.id
    # last_used_at updated
    assert found.last_used_at is not None


def test_authenticate_wrong_key(db: Session) -> None:
    t = _tenant(db)
    api_key_service.create_key(db, tenant=t, name="X", scopes=["read:services"])
    assert api_key_service.authenticate(db, "pk_live_00000000deadbeef") is None


def test_authenticate_empty(db: Session) -> None:
    assert api_key_service.authenticate(db, "") is None
    assert api_key_service.authenticate(db, "wrong_prefix") is None


def test_authenticate_revoked(db: Session) -> None:
    t = _tenant(db)
    row, plaintext = api_key_service.create_key(db, tenant=t, name="X", scopes=["read:services"])
    api_key_service.revoke_key(db, t, row.id)
    assert api_key_service.authenticate(db, plaintext) is None


def test_authenticate_expired(db: Session) -> None:
    t = _tenant(db)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    row, plaintext = api_key_service.create_key(
        db, tenant=t, name="X", scopes=["read:services"], expires_at=past,
    )
    assert api_key_service.authenticate(db, plaintext) is None


def test_authenticate_not_expired(db: Session) -> None:
    t = _tenant(db)
    future = datetime.now(timezone.utc) + timedelta(days=30)
    row, plaintext = api_key_service.create_key(
        db, tenant=t, name="X", scopes=["read:services"], expires_at=future,
    )
    assert api_key_service.authenticate(db, plaintext) is not None


# ---------- has_scope ----------


def test_has_scope(db: Session) -> None:
    t = _tenant(db)
    row, _ = api_key_service.create_key(db, tenant=t, name="X", scopes=["read:services", "read:bookings"])
    assert api_key_service.has_scope(row, "read:services")
    assert api_key_service.has_scope(row, "read:bookings")
    assert not api_key_service.has_scope(row, "read:reviews")
