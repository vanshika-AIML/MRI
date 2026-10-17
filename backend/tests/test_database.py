"""Database connection and migration tests."""
import pytest
from sqlalchemy import text

from tests.conftest import requires_db


@requires_db
class TestDatabaseConnection:
    """Verify basic database connectivity."""

    def test_connect_and_query(self, db_session):
        """The application can connect and execute a trivial query."""
        result = db_session.execute(text("SELECT 1 AS x"))
        assert result.scalar() == 1

    def test_pgvector_extension_loaded(self, db_session):
        """The pgvector extension is available."""
        result = db_session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        assert result.scalar() == "vector"
