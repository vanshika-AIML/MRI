"""Pytest configuration and fixtures for the backend test suite.

Database tests use a dedicated test database (derived from DATABASE_URL with
``_test`` suffix) and transactional isolation — every test runs inside a
transaction that is rolled back at the end so tests never pollute each other.

Tests that require a live database are automatically skipped when
DATABASE_URL is not set, keeping Phase 1/2 tests runnable without any
database.
"""
import os
os.environ["RATE_LIMIT_ENABLED"] = "false"
from pathlib import Path
import sys
import uuid

# Ensure workspace root is in sys.path for importing ml packages
_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Derive a test DATABASE_URL
# ---------------------------------------------------------------------------

_BASE_URL = os.environ.get("DATABASE_URL") or ""

# Compute a test-database URL by appending "_test" to the database name
# unless the user explicitly provides TEST_DATABASE_URL.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

if not TEST_DATABASE_URL and _BASE_URL:
    # e.g. postgresql+psycopg://user:pw@localhost:5432/mri_db
    #   -> postgresql+psycopg://user:pw@localhost:5432/mri_db_test
    if "/" in _BASE_URL:
        TEST_DATABASE_URL = _BASE_URL + "_test"

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

requires_db = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL / DATABASE_URL not set — skipping database tests",
)

# ---------------------------------------------------------------------------
# Database engine / session fixtures (scoped to the test session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine():
    """Create the test database (if it does not exist) and return an engine.

    The engine connects to ``<DATABASE_URL>_test``.
    """
    if not TEST_DATABASE_URL:
        pytest.skip("No database URL configured")

    # First, ensure the test database exists.
    # Connect to the *default* postgres database to issue CREATE DATABASE.
    base_url_parts = TEST_DATABASE_URL.rsplit("/", 1)
    admin_url = base_url_parts[0] + "/postgres"
    test_db_name = base_url_parts[1] if len(base_url_parts) > 1 else "mri_db_test"

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
    with admin_engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db"),
            {"db": test_db_name},
        )
        if not result.fetchone():
            conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
    admin_engine.dispose()

    engine = create_engine(TEST_DATABASE_URL, echo=False, connect_args={"connect_timeout": 5})

    # Enable pgvector and create all tables
    from app.db.base import Base
    import app.models  # noqa: F401 — register all models

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    from alembic.config import Config
    from alembic import command
    config = Config(str(_WORKSPACE_ROOT / "backend/alembic.ini"))
    config.set_main_option("script_location", str(_WORKSPACE_ROOT / "backend/alembic"))
    config.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(config, "head")

    yield engine

    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Session:
    """Provide a transactional database session that rolls back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()
