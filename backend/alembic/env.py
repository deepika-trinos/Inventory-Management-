"""Alembic environment: tells Alembic WHICH database to migrate and WHICH tables exist.

Database address, in order of priority:
1. ``config.attributes["database_url"]``: set by code (the pytest setup uses
   this to migrate the TEST database).
2. ``DATABASE_URL`` from backend/.env (normal ``alembic upgrade head``).
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.core.config import get_settings
from app.models import Base  # importing app.models registers every table

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Alembic compares this with the real database when you run
# "alembic revision --autogenerate".
target_metadata = Base.metadata


def get_url() -> str:
    return config.attributes.get("database_url") or get_settings().database_url


def run_migrations_offline() -> None:
    """'Offline' mode: print the SQL instead of running it (alembic upgrade head --sql)."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Normal mode: connect to the database and apply the migrations."""
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # also detect column type changes
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
