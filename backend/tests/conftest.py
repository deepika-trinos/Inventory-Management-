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

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


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
