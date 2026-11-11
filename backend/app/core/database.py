"""Database connection (SQLAlchemy 2.x).

- ``engine``       : the connection pool to PostgreSQL, created once.
- ``SessionLocal`` : a factory that makes a new database session.
- ``get_db``       : a FastAPI dependency that gives each request its OWN
                     session and always closes it afterwards.
- ``Base``         : the parent class every database table model will inherit from.
"""

from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# pool_pre_ping checks a connection is still alive before using it.
# connect_timeout (seconds) stops requests hanging when PostgreSQL is down;
# without it, a connection attempt on Windows can wait for minutes.
engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Predictable names for constraints and indexes, so Alembic migrations stay
# readable and can later drop/rename them reliably.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def get_db() -> Generator[Session, None, None]:
    """One database session per request.

    FastAPI runs the code before ``yield`` when a request starts, hands the
    session to the route, and runs the ``finally`` block when the request ends,
    even if an error happened.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
