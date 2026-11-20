"""Development-only reset_password script (decision D8)."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.audit.models import AuditLog
from app.modules.users.models import User
from app.scripts import reset_password

NEW_PASSWORD = "a-brand-new-long-password"


def typed(monkeypatch, *passwords):
    answers = iter(passwords)
    monkeypatch.setattr("getpass.getpass", lambda _: next(answers))


def stored(user_id: int) -> User:
    with SessionLocal() as fresh:
        user = fresh.get(User, user_id)
        fresh.expunge_all()
        return user


def test_new_password_works_and_the_old_one_stops_working(client, make_user, monkeypatch, capsys):
    user, old_password = make_user("Admin")
    typed(monkeypatch, NEW_PASSWORD, NEW_PASSWORD)

    assert reset_password.main(["--email", user.email.upper()]) == 0  # any case

    assert f"New password set for {user.email}" in capsys.readouterr().out
    login = lambda pw: client.post("/api/v1/auth/login", json={"email": user.email, "password": pw})  # noqa: E731
    assert login(NEW_PASSWORD).status_code == 200
    assert login(old_password).status_code == 401


def test_only_the_password_changes_and_an_audit_row_is_written(make_user, monkeypatch, capsys):
    user, _ = make_user("IT Manager")
    before = stored(user.id)
    typed(monkeypatch, NEW_PASSWORD, NEW_PASSWORD)

    assert reset_password.main(["--email", user.email]) == 0

    after = stored(user.id)
    assert after.password_hash != before.password_hash
    assert (after.role_id, after.is_active, after.employee_id) == (before.role_id, before.is_active, before.employee_id)
    with SessionLocal() as fresh:
        [row] = fresh.scalars(
            select(AuditLog).where(AuditLog.action == "user.updated", AuditLog.entity_id == str(user.id))
        ).all()
    assert row.actor_user_id is None
    assert row.after_data == {"change": "password reset with the development script"}
    assert NEW_PASSWORD not in str(row.after_data) + str(row.before_data)
    assert NEW_PASSWORD not in capsys.readouterr().out


def test_asks_for_the_email_when_not_given(make_user, monkeypatch):
    user, _ = make_user("Admin")
    monkeypatch.setattr("builtins.input", lambda _: user.email)
    typed(monkeypatch, NEW_PASSWORD, NEW_PASSWORD)
    assert reset_password.main([]) == 0


def test_deactivated_login_stays_deactivated_with_a_note(make_user, monkeypatch, capsys):
    user, _ = make_user("Admin", is_active=False)
    typed(monkeypatch, NEW_PASSWORD, NEW_PASSWORD)

    assert reset_password.main(["--email", user.email]) == 0

    assert stored(user.id).is_active is False
    assert "deactivated" in capsys.readouterr().out


def test_unknown_email_changes_nothing(db, monkeypatch, capsys):
    typed(monkeypatch, NEW_PASSWORD, NEW_PASSWORD)
    assert reset_password.main(["--email", "nobody@example.com"]) == 1
    assert "no login with the email" in capsys.readouterr().err


def test_short_password_changes_nothing(make_user, monkeypatch, capsys):
    user, _ = make_user("Admin")
    typed(monkeypatch, "short", "short")

    assert reset_password.main(["--email", user.email]) == 1

    assert "at least 12 characters" in capsys.readouterr().err
    assert stored(user.id).password_hash == user.password_hash


def test_passwords_that_do_not_match_change_nothing(make_user, monkeypatch):
    user, _ = make_user("Admin")
    typed(monkeypatch, NEW_PASSWORD, "something-else-entirely")

    with pytest.raises(SystemExit):
        reset_password.main(["--email", user.email])

    assert stored(user.id).password_hash == user.password_hash


def test_refuses_to_run_in_production(make_user, monkeypatch, capsys):
    user, _ = make_user("Admin")
    monkeypatch.setattr(reset_password, "get_settings", lambda: SimpleNamespace(is_production=True))

    assert reset_password.main(["--email", user.email]) == 1

    assert "development only" in capsys.readouterr().err
    assert stored(user.id).password_hash == user.password_hash
