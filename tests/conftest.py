"""Pytest fixtures for Platform-X tests (speed-optimized)."""

import os
import tempfile

# Set env vars BEFORE importing app modules.
# Use minimal bcrypt rounds in tests (default 12 is ~10x slower).
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ["RATE_LIMIT_ENABLED"] = "false"

_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db", prefix="platform_x_test_")
os.close(_tmp_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db_path}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

import app.models  # noqa: E402,F401  (register all models with Base.metadata)
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402

engine = create_engine(
    f"sqlite:///{_tmp_db_path}",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)

# Create schema ONCE per session — drop at end.
Base.metadata.create_all(bind=engine)


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Drop all tables and remove the temp DB file at the end."""
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        os.unlink(_tmp_db_path)
    except OSError:
        pass


@pytest.fixture(scope="function", autouse=True)
def _clean_tables() -> None:
    """Fast TRUNCATE-like cleanup between tests instead of drop_all/create_all."""
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db() -> Session:
    """Direct DB session for test setup/asserts."""
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def sample_tenant(db: Session) -> Tenant:
    """A default active tenant."""
    t = Tenant(
        slug="demo",
        name="Demo Business",
        tier="starter",
        status="active",
        config={},
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.fixture
def client(db: Session):
    """FastAPI test client with DB override."""

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(client, db):
    """Test client authenticated as a platform admin.

    Creates an admin, logs in, and returns (client, headers) tuple.
    """
    from app.services import admin_service

    admin_service.create(
        db,
        email="admin@example.com",
        password="AdminPass1234",
        name="Test Admin",
        role="super_admin",
    )
    resp = client.post(
        "/platform/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass1234"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}
