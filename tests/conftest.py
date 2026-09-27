"""Pytest fixtures for Platform-X tests."""

import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Set DB to a temp file BEFORE importing app modules
_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db", prefix="platform_x_test_")
os.close(_tmp_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db_path}"
os.environ["SECRET_KEY"] = "test-secret-key"

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402

# Dedicated engine for tests
engine = create_engine(
    f"sqlite:///{_tmp_db_path}",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="function", autouse=True)
def _setup_db() -> Generator[None, None, None]:
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Generator[Session, None, None]:
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
def client(db: Session) -> Generator[TestClient, None, None]:
    """FastAPI test client with DB override."""

    def _override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
