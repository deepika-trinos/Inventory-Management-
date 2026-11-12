"""Database rules for users and roles (Slice 1.3)."""

from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError
from app.modules.employees.models import Employee
from app.modules.users.models import Role, User
from app.modules.users.service import create_user


def test_three_roles_are_seeded(db):
    names = db.scalars(select(Role.name).order_by(Role.id)).all()

    assert names == ["Admin", "IT Manager", "Employee"]


def test_password_is_stored_as_argon2_hash_not_plain_text(make_user):
    user, password = make_user()

    assert user.password_hash.startswith("$argon2")
    assert password not in user.password_hash


def test_same_password_gives_different_hashes(make_user, db):
    first, _ = make_user()
    second = create_user(
        db, email="second@example.com", password="same-password-123", role_name="IT Manager"
    )
    third = create_user(
        db, email="third@example.com", password="same-password-123", role_name="IT Manager"
    )

    assert second.password_hash != third.password_hash  # random salt
    assert first.password_hash != second.password_hash


def test_email_is_saved_in_lower_case(db):
    user = create_user(db, email="  Ravi@Example.COM ", password="long-enough-pw", role_name="Admin")

    assert user.email == "ravi@example.com"


def test_duplicate_email_in_other_case_is_refused_by_service(db):
    create_user(db, email="dup@example.com", password="long-enough-pw", role_name="IT Manager")

    with pytest.raises(AppError) as exc:
        create_user(db, email="DUP@example.com", password="long-enough-pw", role_name="IT Manager")
    assert exc.value.code == "email_taken"


def test_duplicate_email_in_other_case_is_refused_by_database(db, make_user):
    user, _ = make_user(email="case@example.com")
    db.add(User(email="CASE@EXAMPLE.COM", password_hash="x", role_id=user.role_id))

    with pytest.raises(IntegrityError, match="uq_users_email_lower"):
        db.commit()
    db.rollback()


def test_user_must_have_a_role(db):
    db.add(User(email="norole@example.com", password_hash="x"))

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_short_password_is_refused(db):
    with pytest.raises(AppError) as exc:
        create_user(db, email="short@example.com", password="short", role_name="Employee")
    assert exc.value.code == "weak_password"


def test_user_can_be_linked_to_one_employee_only(db):
    employee = Employee(employee_code="EMP-001", full_name="Asha K")
    db.add(employee)
    db.commit()

    linked = create_user(
        db, email="asha@example.com", password="long-enough-pw",
        role_name="Employee", employee_id=employee.id,
    )
    assert linked.employee.employee_code == "EMP-001"

    with pytest.raises(AppError) as exc:
        create_user(
            db, email="other@example.com", password="long-enough-pw",
            role_name="Employee", employee_id=employee.id,
        )
    assert exc.value.code == "employee_has_login"


def test_timestamps_are_timezone_aware_utc(make_user):
    user, _ = make_user()

    assert user.created_at.tzinfo is not None
    assert user.created_at.utcoffset() == timedelta(0)
