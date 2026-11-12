"""Employee-role users must be linked to an employee (Slice 2.2: order fix b, R3, B12)."""

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.modules.audit.models import AuditLog
from app.modules.employees.models import Employee
from app.modules.users import service
from app.modules.users.models import Role, User
from tests.conftest import auth_header

USERS = "/api/v1/users"
TEMP_PASSWORD = "temporary-pass-123"


@pytest.fixture
def admin_session(make_user, login):
    admin, password = make_user("Admin")
    return admin, auth_header(login(admin.email, password))


@pytest.fixture
def new_employee(db):
    counter = iter(range(1, 1000))

    def _make(*, status: str = "active") -> Employee:
        employee = Employee(employee_code=f"LINK-{next(counter)}", full_name="Linked Person", status=status)
        db.add(employee)
        db.commit()
        return employee

    return _make


def audit_rows(user_id: int, action: str) -> list[AuditLog]:
    with SessionLocal() as fresh:
        return list(
            fresh.scalars(
                select(AuditLog)
                .where(AuditLog.entity_type == "users", AuditLog.entity_id == str(user_id), AuditLog.action == action)
                .order_by(AuditLog.id)
            ).all()
        )


def make_legacy_unlinked_employee_user(db) -> User:
    """An Employee-role user created BEFORE Slice 2.2, when the link was optional."""
    user = service.create_user(db, email="legacy@example.com", password=TEMP_PASSWORD, role_name="IT Manager")
    user.role = db.scalar(select(Role).where(Role.name == "Employee"))  # bypasses today's rule on purpose
    db.commit()
    return user


# ---- Create ---------------------------------------------------------------------------
def test_employee_role_user_without_link_is_rejected(client, admin_session):
    _, headers = admin_session

    response = client.post(USERS, headers=headers, json={"email": "e@example.com", "password": TEMP_PASSWORD, "role": "Employee"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "employee_link_required"
    with SessionLocal() as fresh:
        assert fresh.scalar(select(User).where(User.email == "e@example.com")) is None


def test_employee_role_user_with_link_is_created(client, admin_session, new_employee):
    admin, headers = admin_session
    employee = new_employee()

    response = client.post(
        USERS, headers=headers,
        json={"email": "e@example.com", "password": TEMP_PASSWORD, "role": "Employee", "employee_id": employee.id},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["employee"]["employee_code"] == employee.employee_code
    assert body["needs_employee_link"] is False
    [row] = audit_rows(body["id"], "user.created")
    assert row.after_data["employee_id"] == employee.id


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_other_roles_may_be_created_without_a_link(client, admin_session, role):
    _, headers = admin_session

    response = client.post(USERS, headers=headers, json={"email": "o@example.com", "password": TEMP_PASSWORD, "role": role})

    assert response.status_code == 201
    assert response.json()["needs_employee_link"] is False


def test_inactive_employee_cannot_be_linked(client, admin_session, new_employee):
    _, headers = admin_session
    employee = new_employee(status="inactive")

    response = client.post(
        USERS, headers=headers,
        json={"email": "e@example.com", "password": TEMP_PASSWORD, "role": "Employee", "employee_id": employee.id},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "employee_inactive"


def test_one_employee_has_at_most_one_login(client, admin_session, make_user):
    _, headers = admin_session
    existing, _ = make_user("Employee")

    response = client.post(
        USERS, headers=headers,
        json={"email": "two@example.com", "password": TEMP_PASSWORD, "role": "IT Manager", "employee_id": existing.employee_id},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "employee_has_login"


# ---- Edit -------------------------------------------------------------------------------
def test_employee_role_user_link_cannot_be_removed(client, admin_session, make_user):
    _, headers = admin_session
    user, _ = make_user("Employee")

    response = client.patch(f"{USERS}/{user.id}", headers=headers, json={"employee_id": None})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "employee_link_required"
    with SessionLocal() as fresh:
        assert fresh.get(User, user.id).employee_id == user.employee_id


def test_changing_the_link_writes_link_audit_row(client, admin_session, make_user, new_employee):
    admin, headers = admin_session
    user, _ = make_user("Employee")
    old_id = user.employee_id
    target = new_employee()

    response = client.patch(f"{USERS}/{user.id}", headers=headers, json={"employee_id": target.id})

    assert response.status_code == 200
    assert response.json()["employee"]["id"] == target.id
    [row] = audit_rows(user.id, "user.employee_link_changed")
    assert row.actor_user_id == admin.id
    assert row.before_data["employee_id"] == old_id
    assert row.after_data == {"employee_id": target.id, "employee_code": target.employee_code}
    assert audit_rows(user.id, "user.updated") == []  # only the link changed


def test_email_and_link_change_together_write_both_rows(client, admin_session, make_user, new_employee):
    _, headers = admin_session
    user, _ = make_user("IT Manager")
    target = new_employee()

    response = client.patch(
        f"{USERS}/{user.id}", headers=headers, json={"email": "moved@example.com", "employee_id": target.id}
    )

    assert response.status_code == 200
    assert len(audit_rows(user.id, "user.updated")) == 1
    [link_row] = audit_rows(user.id, "user.employee_link_changed")
    assert (link_row.before_data["employee_id"], link_row.after_data["employee_id"]) == (None, target.id)


def test_non_employee_role_link_can_be_removed(client, admin_session, make_user, new_employee):
    _, headers = admin_session
    employee = new_employee()
    user, _ = make_user("IT Manager", employee_id=employee.id)

    response = client.patch(f"{USERS}/{user.id}", headers=headers, json={"employee_id": None})

    assert response.status_code == 200 and response.json()["employee"] is None
    [row] = audit_rows(user.id, "user.employee_link_changed")
    assert row.after_data == {"employee_id": None, "employee_code": None}


def test_failed_link_audit_saves_nothing(db, make_user, new_employee, monkeypatch):
    from app.modules.audit import service as audit

    user, _ = make_user("IT Manager")
    target = new_employee()
    monkeypatch.setattr(audit, "record", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("audit down")))

    with pytest.raises(RuntimeError):
        service.update_user(db, actor=None, user=user, changes={"employee_id": target.id})

    with SessionLocal() as fresh:
        assert fresh.get(User, user.id).employee_id is None


# ---- Role change ------------------------------------------------------------------------
def test_role_change_to_employee_needs_a_link(client, admin_session, make_user):
    _, headers = admin_session
    user, _ = make_user("IT Manager")

    response = client.patch(f"{USERS}/{user.id}/role", headers=headers, json={"role": "Employee"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "employee_link_required"
    with SessionLocal() as fresh:
        assert fresh.get(User, user.id).role.name == "IT Manager"


def test_role_change_to_employee_can_link_in_the_same_step(client, admin_session, make_user, new_employee):
    admin, headers = admin_session
    user, _ = make_user("IT Manager")
    employee = new_employee()

    response = client.patch(
        f"{USERS}/{user.id}/role", headers=headers, json={"role": "Employee", "employee_id": employee.id}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role"]["name"] == "Employee" and body["employee"]["id"] == employee.id
    [role_row] = audit_rows(user.id, "user.role_changed")
    [link_row] = audit_rows(user.id, "user.employee_link_changed")
    assert role_row.after_data["employee_id"] == employee.id
    assert link_row.actor_user_id == admin.id


def test_role_change_to_employee_when_already_linked(client, admin_session, make_user, new_employee):
    _, headers = admin_session
    employee = new_employee()
    user, _ = make_user("IT Manager", employee_id=employee.id)

    response = client.patch(f"{USERS}/{user.id}/role", headers=headers, json={"role": "Employee"})

    assert response.status_code == 200
    assert audit_rows(user.id, "user.employee_link_changed") == []


def test_role_change_away_from_employee_keeps_the_link(client, admin_session, make_user):
    _, headers = admin_session
    user, _ = make_user("Employee")

    response = client.patch(f"{USERS}/{user.id}/role", headers=headers, json={"role": "IT Manager"})

    assert response.status_code == 200
    assert response.json()["employee"]["id"] == user.employee_id


# ---- R3: Employee users created before Slice 2.2 without a link ---------------------------
def test_r3_unlinked_employee_user_can_still_log_in_and_is_flagged(client, admin_session, db, login):
    _, headers = admin_session
    legacy = make_legacy_unlinked_employee_user(db)

    token = login(legacy.email, TEMP_PASSWORD)  # login still works (R3)
    me = client.get("/api/v1/auth/me", headers=auth_header(token))
    listed = client.get(USERS, headers=headers, params={"role": "Employee"}).json()["items"]

    assert me.status_code == 200
    assert [u["needs_employee_link"] for u in listed if u["id"] == legacy.id] == [True]


def test_r3_admin_links_the_unlinked_user(client, admin_session, db, new_employee):
    _, headers = admin_session
    legacy = make_legacy_unlinked_employee_user(db)
    employee = new_employee()

    response = client.patch(f"{USERS}/{legacy.id}", headers=headers, json={"employee_id": employee.id})

    assert response.status_code == 200
    assert response.json()["needs_employee_link"] is False
    assert len(audit_rows(legacy.id, "user.employee_link_changed")) == 1


def test_r3_unlinked_user_can_still_be_edited_and_deactivated(client, admin_session, db):
    _, headers = admin_session
    legacy = make_legacy_unlinked_employee_user(db)

    email = client.patch(f"{USERS}/{legacy.id}", headers=headers, json={"email": "legacy2@example.com"})
    off = client.post(f"{USERS}/{legacy.id}/deactivate", headers=headers)

    assert email.status_code == 200 and off.status_code == 200


def test_service_rule_applies_to_scripts_too(db):
    with pytest.raises(AppError) as exc:
        service.create_user(db, email="s@example.com", password=TEMP_PASSWORD, role_name="Employee")
    assert exc.value.code == "employee_link_required"


# ---- Dev script ---------------------------------------------------------------------------
def test_create_user_script_needs_employee_code_for_employee_role(db, new_employee, monkeypatch, capsys):
    from app.scripts import create_user

    employee = new_employee()
    monkeypatch.setattr("builtins.input", lambda _: "script.emp@example.com")
    monkeypatch.setattr("getpass.getpass", lambda _: TEMP_PASSWORD)

    assert create_user.main(["--role", "Employee"]) == 1
    assert "--employee-code is required" in capsys.readouterr().err
    assert create_user.main(["--role", "Employee", "--employee-code", "NOPE"]) == 1
    assert create_user.main(["--role", "Employee", "--employee-code", employee.employee_code.lower()]) == 0

    with SessionLocal() as fresh:
        assert fresh.scalar(select(User).where(User.email == "script.emp@example.com")).employee_id == employee.id
