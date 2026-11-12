"""The create_admin seed script (Slice 1.3, order fix a)."""

from sqlalchemy import select

from app.modules.users.models import User
from app.scripts import create_admin
from app.scripts._prompt import SeedSettings


def test_create_admin_from_environment_variables(db, monkeypatch, capsys):
    monkeypatch.setenv("ADMIN_EMAIL", "First.Admin@Example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-long-test-password")

    assert create_admin.main() == 0

    admin = db.scalar(select(User).where(User.email == "first.admin@example.com"))
    assert admin is not None
    assert admin.role.name == "Admin"
    assert admin.password_hash.startswith("$argon2")
    assert "a-long-test-password" not in capsys.readouterr().out  # never printed


def test_create_admin_does_nothing_when_an_admin_exists(db, make_user, monkeypatch, capsys):
    make_user("Admin")
    monkeypatch.setenv("ADMIN_EMAIL", "second@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-long-test-password")

    assert create_admin.main() == 0

    assert "already exists" in capsys.readouterr().out
    assert db.scalar(select(User).where(User.email == "second@example.com")) is None


def test_create_admin_refuses_a_short_password(db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "short")

    assert create_admin.main() == 1
    assert db.scalar(select(User)) is None


def test_create_admin_asks_when_no_environment_variables(db, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    # Ignore the developer's backend/.env too: it may hold ADMIN_EMAIL / ADMIN_PASSWORD.
    monkeypatch.setattr(create_admin, "SeedSettings", lambda: SeedSettings(_env_file=None))
    monkeypatch.setattr("builtins.input", lambda _: "typed.admin@example.com")
    monkeypatch.setattr("getpass.getpass", lambda _: "typed-long-password")

    assert create_admin.main() == 0
    assert db.scalar(select(User).where(User.email == "typed.admin@example.com")) is not None
