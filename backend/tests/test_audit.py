"""Audit log foundation (Slice 1.4, BR-13).

The role change here is SIMULATED through the service layer (users.service.change_role),
because the role-change endpoint arrives in Slice 1.6, which will re-check this
through the real feature.
"""

from datetime import timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.database import SessionLocal, utc_now
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditContext
from app.modules.users.models import User
from app.modules.users.service import change_role, get_role_by_name


SETUP_ACTION = "user.created"  # written by the make_user fixture since Slice 1.6


def audit_rows() -> list[AuditLog]:
    """Read audit rows through a FRESH session: only what was really saved.
    Rows written while creating the test users are left out."""
    with SessionLocal() as fresh:
        return list(
            fresh.scalars(
                select(AuditLog).where(AuditLog.action != SETUP_ACTION).order_by(AuditLog.id)
            ).all()
        )


def role_in_database(user_id: int) -> str:
    with SessionLocal() as fresh:
        return fresh.get(User, user_id).role.name


# ---- The "done when" checks ---------------------------------------------------------
def test_simulated_role_change_writes_audit_row_with_admin_and_time(db, make_user):
    admin, _ = make_user("Admin")
    employee, _ = make_user("Employee")
    started = utc_now()

    change_role(db, actor=admin, user=employee, new_role_name="IT Manager")

    rows = audit_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row.actor_user_id == admin.id
    assert row.action == "user.role_changed"
    assert (row.entity_type, row.entity_id) == ("users", str(employee.id))
    assert row.before_data["role"] == "Employee"
    assert row.after_data["role"] == "IT Manager"
    assert row.after_data["is_active"] is True  # status is shown too
    assert row.created_at.utcoffset() == timedelta(0)  # stored in UTC
    assert started - timedelta(seconds=5) <= row.created_at <= utc_now() + timedelta(seconds=5)
    assert role_in_database(employee.id) == "IT Manager"


def test_rolled_back_role_change_writes_nothing(db, make_user):
    admin, _ = make_user("Admin")
    employee, _ = make_user("Employee")

    # Do the change and record it, then something fails before the commit.
    before = audit.snapshot(employee, ["role"])
    employee.role = get_role_by_name(db, "Admin")
    audit.record(
        db, actor=admin, action=AuditAction.USER_ROLE_CHANGED, entity=employee,
        before=before, after=audit.snapshot(employee, ["role"]),
    )
    db.rollback()  # e.g. a later step in the same operation raised an error

    assert audit_rows() == []
    assert role_in_database(employee.id) == "Employee"


def test_change_role_that_fails_at_commit_saves_neither_change_nor_audit(db, make_user, monkeypatch):
    admin, _ = make_user("Admin")
    employee, _ = make_user("Employee")

    def failing_commit():
        raise RuntimeError("database went away")

    monkeypatch.setattr(db, "commit", failing_commit)

    with pytest.raises(RuntimeError):
        change_role(db, actor=admin, user=employee, new_role_name="Admin")

    assert audit_rows() == []
    assert role_in_database(employee.id) == "Employee"


def test_if_audit_row_cannot_be_saved_the_business_change_is_undone(db, make_user):
    employee, _ = make_user("Employee")
    ghost_actor = User(id=999_999, email="ghost@example.com")  # not in the database

    with pytest.raises(IntegrityError):
        change_role(db, actor=ghost_actor, user=employee, new_role_name="Admin")

    assert audit_rows() == []
    assert role_in_database(employee.id) == "Employee"


def test_no_audit_row_when_role_does_not_change(db, make_user):
    admin, _ = make_user("Admin")
    employee, _ = make_user("Employee")

    change_role(db, actor=admin, user=employee, new_role_name="Employee")

    assert audit_rows() == []


# ---- The helper ---------------------------------------------------------------------
def test_record_joins_the_callers_transaction_and_does_not_commit(db, make_user):
    admin, _ = make_user("Admin")

    audit.record(db, actor=admin, action=AuditAction.USER_UPDATED, entity=admin, after={"x": 1})

    in_this_session = db.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.action != SETUP_ACTION)
    )
    assert in_this_session == 1  # visible in this session
    assert audit_rows() == []  # but not saved yet
    db.commit()
    assert len(audit_rows()) == 1


def test_password_hash_and_other_secrets_are_removed(db, make_user):
    admin, _ = make_user("Admin")

    audit.record(
        db,
        actor=admin,
        action=AuditAction.USER_UPDATED,
        entity=admin,
        before={"email": "a@example.com", "password_hash": "$argon2id$abc", "is_active": True},
        after={
            "email": "b@example.com",
            "Password": "plain-text",
            "access_token": "eyJ...",
            "nested": {"refresh_token": "r", "jwt_secret_key": "s", "keep": "yes"},
            "items": [{"new_password": "p", "name": "mouse"}],
        },
    )
    db.commit()

    row = audit_rows()[0]
    assert row.before_data == {"email": "a@example.com", "is_active": True}
    assert row.after_data == {
        "email": "b@example.com",
        "nested": {"keep": "yes"},
        "items": [{"name": "mouse"}],
    }


def test_values_are_stored_as_json_friendly_text(db, make_user):
    admin, _ = make_user("Admin")

    audit.record(
        db, actor=admin, action=AuditAction.USER_UPDATED, entity=admin,
        after=audit.snapshot(admin, ["email", "is_active", "created_at", "role"]),
    )
    db.commit()

    after = audit_rows()[0].after_data
    assert after["role"] == "Admin"
    assert after["is_active"] is True
    assert after["created_at"].startswith(str(admin.created_at.date()))


def test_unknown_action_name_is_refused(db, make_user):
    admin, _ = make_user("Admin")

    with pytest.raises(ValueError, match="Unknown audit action"):
        audit.record(db, actor=admin, action="user.rolechanged", entity=admin)


def test_system_action_has_no_actor(db):
    audit.record(db, actor=None, action=AuditAction.STOCK_ADJUSTED, entity_type="inventory_items", entity_id=7)
    db.commit()

    row = audit_rows()[0]
    assert row.actor_user_id is None
    assert (row.entity_type, row.entity_id) == ("inventory_items", "7")


def test_ip_address_and_request_id_are_stored(db, make_user):
    admin, _ = make_user("Admin")

    audit.record(
        db, actor=admin, action=AuditAction.USER_UPDATED, entity=admin,
        context=AuditContext(ip_address="192.168.1.20", request_id="req-123"),
    )
    db.commit()

    row = audit_rows()[0]
    assert str(row.ip_address) == "192.168.1.20"
    assert row.request_id == "req-123"


def test_action_list_has_the_agreed_names():
    assert AuditAction.all() == {
        "user.created", "user.updated", "user.role_changed", "user.activated",
        "user.deactivated",
        "category.created", "category.updated", "category.activated", "category.deactivated",  # Slice 2.1
        "purchase.received", "purchase.cancelled", "asset.created",
        "asset.retired", "assignment.created", "assignment.returned", "stock.issued",
        "stock.adjusted", "maintenance.status_changed",
    }


# ---- Append-only --------------------------------------------------------------------
def _saved_row(db, actor) -> AuditLog:
    row = audit.record(db, actor=actor, action=AuditAction.USER_UPDATED, entity=actor, after={"a": 1})
    db.commit()
    return row


def test_app_refuses_to_change_an_audit_row(db, make_user):
    admin, _ = make_user("Admin")
    row = _saved_row(db, admin)

    row.action = "user.created"
    with pytest.raises(PermissionError):
        db.flush()
    db.rollback()


def test_app_refuses_to_delete_an_audit_row(db, make_user):
    admin, _ = make_user("Admin")
    row = _saved_row(db, admin)

    db.delete(row)
    with pytest.raises(PermissionError):
        db.flush()
    db.rollback()


@pytest.mark.parametrize(
    "sql",
    ["UPDATE audit_logs SET action = 'user.created'", "DELETE FROM audit_logs"],
)
def test_database_refuses_update_and_delete_even_with_raw_sql(db, make_user, sql):
    admin, _ = make_user("Admin")
    _saved_row(db, admin)

    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text(sql))
    db.rollback()
    assert len(audit_rows()) == 1
