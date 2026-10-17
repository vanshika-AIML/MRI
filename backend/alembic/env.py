"""Alembic environment configuration.

Reads DATABASE_URL from the application settings (which in turn reads
from environment variables / .env).  Imports all ORM models so that
``Base.metadata`` contains every table for autogenerate.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Application imports ───────────────────────────────────────────
from app.core.config import settings
from app.db.base import Base

# Importing the models package ensures all models register with Base.metadata.
import app.models  # noqa: F401

# ── Alembic setup ─────────────────────────────────────────────────
config = context.config

# Override the sqlalchemy.url from the ini file with the application's
# DATABASE_URL so credentials never need to appear in alembic.ini.
if settings.DATABASE_URL:
    config.set_main_option("sqlalchemy.url", config.attributes.get("database_url", settings.DATABASE_URL).replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script generation)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live database connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": 5},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
