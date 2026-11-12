"""Shared pytest setup. pytest runs this file automatically before any test.

Safety rules:
- Tests ALWAYS use TEST_DATABASE_URL, never the development database.
- If TEST_DATABASE_URL is missing or equals DATABASE_URL, tests refuse to run.
- Before the first test, all Alembic migrations are applied to the test
  database, so tests run against the same tables as the real app.
"""

import os
from pathlib import Path

import pytest

from app.core.config import Settings, get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Tests sign tokens with their own throwaway secret, never the developer's.
os.environ["JWT_SECRET_KEY"] = "test-only-secret-not-used-anywhere-else-0123456789"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["PASSWORD_MIN_LENGTH"] = "12"

# Read .env once to find the test database, then point the WHOLE app at it
# BEFORE the app (and its database engine) is imported.
_settings = Settings()
if not _settings.test_database_url:
    pytest.exit("TEST_DATABASE_URL is not set in backend/.env. See README.md.", returncode=2)
if _settings.test_database_url == _settings.database_url:
    pytest.exit("TEST_DATABASE_URL must be different from DATABASE_URL.", returncode=2)

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = _settings.test_database_url
get_settings.cache_clear()

import secrets  # noqa: E402
from collections.abc import Callable  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.users.models import User  # noqa: E402
from app.modules.users.service import create_user  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database():
    """Apply every migration to the test database once per test run."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = get_settings().database_url
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
def client():
    """A fake browser that calls the API in-process (no server needed)."""
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    """A database session on the TEST database. Data tables are emptied after
    each test (the seeded roles stay), so every test starts clean."""
    session = SessionLocal()
    yield session
    session.close()
    with SessionLocal() as cleanup:
        # TRUNCATE is allowed on audit_logs (only UPDATE/DELETE are blocked).
        cleanup.execute(text("TRUNCATE audit_logs, asset_categories, users, employees RESTART IDENTITY CASCADE"))
        cleanup.commit()


@pytest.fixture
def make_user(db) -> Callable[..., tuple[User, str]]:
    """Create a user and return (user, plain_password). Each gets a random password."""
    counter = iter(range(1, 10_000))

    def _make(role: str = "Employee", *, is_active: bool = True, email: str | None = None):
        password = secrets.token_urlsafe(16)
        user = create_user(
            db,
            email=email or f"user{next(counter)}.{role.replace(' ', '').lower()}@example.com",
            password=password,
            role_name=role,
            is_active=is_active,
        )
        return user, password

    return _make


@pytest.fixture
def login(client) -> Callable[[str, str], str]:
    """Log in through the real endpoint and return the access token."""

    def _login(email: str, password: str) -> str:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    return _login


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
