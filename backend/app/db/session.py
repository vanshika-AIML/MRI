"""SQLAlchemy engine, session factory, and FastAPI dependency."""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import logger

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------
# The engine is created lazily the first time it is referenced so the app
# can still boot for Phase-1/2 endpoints even when DATABASE_URL is unset.
# ---------------------------------------------------------------------------

_engine = None
_SessionLocal = None


def _init_engine():
    """Create and cache the engine + session factory on first use."""
    global _engine, _SessionLocal
    if _engine is not None:
        return

    if not settings.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Set it in your .env or environment variables."
        )

    # Set connect_timeout=2 so connection probes fail fast when Postgres is offline
    connect_args = {}
    if "postgresql" in settings.DATABASE_URL.lower():
        connect_args["connect_timeout"] = 2

    _engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args=connect_args,
    )
    _SessionLocal = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
    )
    logger.info("Database engine initialised")


@property
def engine():
    _init_engine()
    return _engine


# Expose a module-level `engine` attribute for Alembic / scripts.
class _EngineProxy:
    """Thin proxy so ``from app.db.session import engine`` works."""
    def __getattr__(self, name):
        _init_engine()
        return getattr(_engine, name)

engine = _EngineProxy()


def SessionLocal() -> Session:  # noqa: N802 — keep factory-style name
    """Return a new SQLAlchemy session.  Initialises engine on first call."""
    _init_engine()
    return _SessionLocal()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Usage in a route::

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    The session is committed if the request succeeds,
    rolled back on exception, and always closed.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
