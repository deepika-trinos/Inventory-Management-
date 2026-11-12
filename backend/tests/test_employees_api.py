"""Employees API (Slice 2.2, EMP-01 to EMP-03, BR-12, BR-13, decision B21)."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.audit.models import AuditLog
from app.modules.employees import service
from app.modules.employees.models import Employee
from app.modules.users.models import User
from tests.conftest import auth_header

EMPLOYEES = "/api/v1/employees"


@pytest.fixture
def staff_headers(make_user, login):
    def _headers(role: str = "IT Manager"):
        user, password = make_user(role)
        return user, auth_header(login(user.email, password))

    return _headers


@pytest.fixture
def manager(staff_headers):
    return staff_headers("IT Manager")


def create(client, headers, **body):
    body = {"employee_code": "EMP-001", "full_name": "Asha Kumar", **body}
    return client.post(EMPLOYEES, headers=headers, json=body)


def audit_for(entity_type: str, entity_id: int, action: str | None = None) -> list[AuditLog]:
    with SessionLocal() as fresh:
        stmt = select(AuditLog).where(AuditLog.entity_type == entity_type, AuditLog.entity_id == str(entity_id))
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return list(fresh.scalars(stmt.order_by(AuditLog.id)).all())


def in_database(employee_id: int) -> Employee | None:
    with SessionLocal() as fresh:
        return fresh.get(Employee, employee_id)


# ---- Roles: Admin and IT Manager only -------------------------------------------------
ENDPOINTS = [
    ("get", EMPLOYEES, None),
    ("get", f"{EMPLOYEES}/departments", None),
    ("post", EMPLOYEES, {"employee_code": "X", "full_name": "Y"}),
    ("get", f"{EMPLOYEES}/1", None),
    ("patch", f"{EMPLOYEES}/1", {"full_name": "Z"}),
    ("post", f"{EMPLOYEES}/1/activate", None),
    ("post", f"{EMPLOYEES}/1/deactivate", None),
]


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_employee_role_gets_403_on_every_employees_endpoint(client, staff_headers, method, url, body):
    _, headers = staff_headers("Employee")

    response = client.request(method, url, json=body, headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_employees_endpoints_need_login(client, method, url, body):
    assert client.request(method, url, json=body).status_code == 401


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_use_every_endpoint(client, staff_headers, role):
    _, headers = staff_headers(role)

    created = create(client, headers, employee_code="NEW-1")
    eid = created.json()["id"]

    assert created.status_code == 201
    assert client.get(EMPLOYEES, headers=headers).status_code == 200
    assert client.get(f"{EMPLOYEES}/departments", headers=headers).status_code == 200
    assert client.get(f"{EMPLOYEES}/{eid}", headers=headers).status_code == 200
    assert client.patch(f"{EMPLOYEES}/{eid}", headers=headers, json={"phone": "12345"}).status_code == 200
    assert client.post(f"{EMPLOYEES}/{eid}/deactivate", headers=headers).status_code == 200
    assert client.post(f"{EMPLOYEES}/{eid}/activate", headers=headers).status_code == 200


# ---- Done-check: the IT Manager adds, finds and deactivates an employee -----------------
def test_it_manager_adds_finds_and_deactivates_an_employee(client, manager):
    user, headers = manager

    created = create(
        client, headers, employee_code=" EMP-042 ", full_name=" Ravi Shah ", department="Finance",
        designation="Accountant", work_email=" Ravi.Shah@Example.COM ", phone="+91 98765 43210",
    )
    eid = created.json()["id"]
    found = client.get(EMPLOYEES, headers=headers, params={"search": "ravi"}).json()
    deactivated = client.post(f"{EMPLOYEES}/{eid}/deactivate", headers=headers)

    assert created.status_code == 201
    body = created.json()
    assert (body["employee_code"], body["full_name"]) == ("EMP-042", "Ravi Shah")
    assert body["work_email"] == "ravi.shah@example.com"  # lower case (B5)
    assert (body["department"], body["designation"], body["phone"]) == ("Finance", "Accountant", "+91 98765 43210")
    assert body["status"] == "active" and body["user"] is None
    assert [e["id"] for e in found["items"]] == [eid]
    assert deactivated.status_code == 200 and deactivated.json()["status"] == "inactive"

    [created_row] = audit_for("employees", eid, "employee.created")
    [deactivated_row] = audit_for("employees", eid, "employee.deactivated")
    assert created_row.actor_user_id == user.id and created_row.before_data is None
    assert created_row.after_data["work_email"] == "ravi.shah@example.com"
    assert (deactivated_row.before_data["status"], deactivated_row.after_data["status"]) == ("active", "inactive")


def test_optional_fields_can_be_left_out(client, manager):
    _, headers = manager

    response = client.post(EMPLOYEES, headers=headers, json={"employee_code": "E1", "full_name": "Min Field"})

    assert response.status_code == 201
    body = response.json()
    assert body["department"] is None and body["work_email"] is None and body["phone"] is None


# ---- Duplicates ------------------------------------------------------------------------
@pytest.mark.parametrize("code", ["EMP-001", "emp-001", "  Emp-001 "])
def test_duplicate_employee_code_is_blocked_in_any_case(client, manager, code):
    _, headers = manager
    assert create(client, headers).status_code == 201

    response = create(client, headers, employee_code=code, full_name="Someone Else")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "employee_code_taken"


def test_duplicate_work_email_is_blocked_in_any_case(client, manager):
    _, headers = manager
    create(client, headers, work_email="asha@example.com")

    response = create(client, headers, employee_code="EMP-002", work_email="ASHA@example.com")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "work_email_taken"


def test_many_employees_can_have_no_work_email(client, manager):
    _, headers = manager
    assert create(client, headers, employee_code="A1").status_code == 201
    assert create(client, headers, employee_code="A2", work_email="  ").status_code == 201


def test_database_indexes_block_case_duplicates_even_without_the_service(db):
    db.add(Employee(employee_code="DB-1", full_name="One", work_email="same@example.com"))
    db.commit()
    for twin in (
        Employee(employee_code="db-1", full_name="Two"),
        Employee(employee_code="DB-2", full_name="Three", work_email="SAME@example.com"),
    ):
        db.add(twin)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


# ---- Validation --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"employee_code": "   ", "full_name": "X"}, "invalid_employee_code"),
        ({"employee_code": "E9", "full_name": "  "}, "invalid_full_name"),
        ({"employee_code": "E9", "full_name": "X", "work_email": "not-an-email"}, "invalid_email"),
        ({"employee_code": "E9", "full_name": "X", "phone": "call me"}, "invalid_phone"),
        ({"full_name": "X"}, "validation_error"),
        ({"employee_code": "E9"}, "validation_error"),
        ({"employee_code": "x" * 31, "full_name": "X"}, "validation_error"),
        ({"employee_code": "E9", "full_name": "X", "phone": "1" * 31}, "validation_error"),
    ],
)
def test_create_validation(client, manager, body, code):
    _, headers = manager

    response = client.post(EMPLOYEES, headers=headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert client.get(EMPLOYEES, headers=headers).json()["total"] == 0  # nothing was saved


# ---- Search, filters, sorting, paging (EMP-03) --------------------------------------------
@pytest.fixture
def sample(client, manager):
    _, headers = manager
    rows = [
        ("EMP-101", "Asha Kumar", "Finance"),
        ("EMP-102", "Ravi Shah", "Engineering"),
        ("EMP-103", "Meera Iyer", "engineering"),
        ("HR-001", "Karan Mehta", "Human Resources"),
        ("EMP-104", "Zoya Khan", None),
    ]
    ids = {}
    for code, name, dept in rows:
        ids[code] = create(client, headers, employee_code=code, full_name=name, department=dept).json()["id"]
    client.post(f"{EMPLOYEES}/{ids['EMP-103']}/deactivate", headers=headers)
    return headers


def names(client, headers, **params):
    body = client.get(EMPLOYEES, headers=headers, params=params).json()
    return [e["full_name"] for e in body["items"] if not e["employee_code"].startswith("TEST-")]


@pytest.mark.parametrize(
    ("search", "expected"),
    [
        ("hr-0", ["Karan Mehta"]),  # by employee ID
        ("SHAH", ["Ravi Shah"]),  # by name
        ("engineer", ["Meera Iyer", "Ravi Shah"]),  # by department, any case
        ("%", []),  # wildcards are plain text
    ],
)
def test_search_by_id_name_or_department(client, sample, search, expected):
    assert names(client, sample, search=search) == expected


def test_filters_sorting_and_paging(client, sample):
    headers = sample

    assert names(client, headers, status="inactive") == ["Meera Iyer"]
    assert names(client, headers, department="ENGINEERING") == ["Meera Iyer", "Ravi Shah"]
    assert names(client, headers, department="Engineering", status="active") == ["Ravi Shah"]
    assert names(client, headers, sort="-employee_code", search="emp-") == [
        "Zoya Khan", "Meera Iyer", "Ravi Shah", "Asha Kumar"
    ]
    page = client.get(EMPLOYEES, headers=headers, params={"page": 2, "page_size": 2, "sort": "full_name"}).json()
    assert page["total"] == 5 and page["page"] == 2 and len(page["items"]) == 2
    assert client.get(EMPLOYEES, headers=headers, params={"sort": "phone"}).status_code == 400


def test_departments_list_one_spelling_each(client, sample):
    response = client.get(f"{EMPLOYEES}/departments", headers=sample)

    assert response.status_code == 200
    assert response.json() == ["Engineering", "Finance", "Human Resources"]


def test_has_login_filter(client, sample, make_user):
    with_login = make_user("Employee")[0].employee.full_name

    without = names(client, sample, has_login="false")
    linked = client.get(EMPLOYEES, headers=sample, params={"has_login": "true"}).json()["items"]

    assert with_login not in without and "Asha Kumar" in without
    assert with_login in [e["full_name"] for e in linked]


def test_get_one_shows_linked_login_and_404(client, manager, make_user):
    _, headers = manager
    user, _ = make_user("Employee")

    found = client.get(f"{EMPLOYEES}/{user.employee_id}", headers=headers)
    missing = client.get(f"{EMPLOYEES}/9999", headers=headers)

    assert found.json()["user"] == {"id": user.id, "email": user.email, "is_active": True}
    assert "password" not in found.text
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "employee_not_found"


# ---- Edit -----------------------------------------------------------------------------------
def test_edit_writes_audit_row_with_before_and_after(client, manager):
    user, headers = manager
    eid = create(client, headers, department="Finance", phone="111").json()["id"]

    response = client.patch(
        f"{EMPLOYEES}/{eid}", headers=headers,
        json={"designation": "Lead", "department": " Accounts ", "phone": None, "work_email": "A.K@Example.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["designation"], body["department"], body["phone"], body["work_email"]) == (
        "Lead", "Accounts", None, "a.k@example.com"
    )
    [row] = audit_for("employees", eid, "employee.updated")
    assert row.actor_user_id == user.id
    assert (row.before_data["department"], row.after_data["department"]) == ("Finance", "Accounts")
    assert (row.before_data["phone"], row.after_data["phone"]) == ("111", None)


def test_edit_with_no_real_change_writes_no_audit_row(client, manager):
    _, headers = manager
    eid = create(client, headers, department="Finance").json()["id"]

    response = client.patch(
        f"{EMPLOYEES}/{eid}", headers=headers, json={"full_name": " Asha Kumar ", "department": "Finance"}
    )

    assert response.status_code == 200
    assert audit_for("employees", eid, "employee.updated") == []


def test_edit_duplicate_code_or_email_is_blocked_but_own_values_are_fine(client, manager):
    _, headers = manager
    create(client, headers, employee_code="EMP-001", work_email="one@example.com")
    eid = create(client, headers, employee_code="EMP-002", work_email="two@example.com").json()["id"]

    code_clash = client.patch(f"{EMPLOYEES}/{eid}", headers=headers, json={"employee_code": "emp-001"})
    email_clash = client.patch(f"{EMPLOYEES}/{eid}", headers=headers, json={"work_email": "ONE@example.com"})
    own_code_case = client.patch(f"{EMPLOYEES}/{eid}", headers=headers, json={"employee_code": "emp-002"})

    assert code_clash.status_code == 409 and code_clash.json()["error"]["code"] == "employee_code_taken"
    assert email_clash.status_code == 409 and email_clash.json()["error"]["code"] == "work_email_taken"
    assert own_code_case.status_code == 200 and own_code_case.json()["employee_code"] == "emp-002"


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"full_name": "  "}, "invalid_full_name"),
        ({"employee_code": ""}, "validation_error"),
        ({"work_email": "nope"}, "invalid_email"),
        ({"phone": "abc"}, "invalid_phone"),
    ],
)
def test_edit_validation(client, manager, body, code):
    _, headers = manager
    eid = create(client, headers).json()["id"]

    response = client.patch(f"{EMPLOYEES}/{eid}", headers=headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_null_for_a_required_field_keeps_it(client, manager):
    _, headers = manager
    eid = create(client, headers).json()["id"]

    response = client.patch(f"{EMPLOYEES}/{eid}", headers=headers, json={"full_name": None})

    assert response.status_code == 200 and response.json()["full_name"] == "Asha Kumar"


def test_inactive_employee_can_still_be_edited(client, manager):
    _, headers = manager
    eid = create(client, headers).json()["id"]
    client.post(f"{EMPLOYEES}/{eid}/deactivate", headers=headers)

    response = client.patch(f"{EMPLOYEES}/{eid}", headers=headers, json={"designation": "Former analyst"})

    assert response.status_code == 200 and response.json()["status"] == "inactive"


# ---- Activate / deactivate, never delete (BR-12) ---------------------------------------------
def test_activate_and_repeat_actions(client, manager):
    _, headers = manager
    eid = create(client, headers).json()["id"]

    client.post(f"{EMPLOYEES}/{eid}/activate", headers=headers)  # already active: nothing
    client.post(f"{EMPLOYEES}/{eid}/deactivate", headers=headers)
    client.post(f"{EMPLOYEES}/{eid}/deactivate", headers=headers)  # already inactive: nothing
    reactivated = client.post(f"{EMPLOYEES}/{eid}/activate", headers=headers)

    assert reactivated.json()["status"] == "active"
    assert [r.action for r in audit_for("employees", eid)] == [
        "employee.created", "employee.deactivated", "employee.activated"
    ]


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_there_is_no_delete(client, staff_headers, role):
    _, headers = staff_headers(role)
    eid = create(client, headers, employee_code=f"DEL-{role}").json()["id"]

    response = client.delete(f"{EMPLOYEES}/{eid}", headers=headers)

    assert response.status_code == 405
    assert in_database(eid) is not None
    assert not hasattr(service, "delete_employee")


def test_activate_or_deactivate_missing_employee_is_404(client, manager):
    _, headers = manager
    assert client.post(f"{EMPLOYEES}/9999/deactivate", headers=headers).status_code == 404
    assert client.post(f"{EMPLOYEES}/9999/activate", headers=headers).status_code == 404


# ---- Deactivating an employee also deactivates the linked login (B21) -------------------------
def test_deactivating_employee_deactivates_linked_login(client, manager, make_user, login):
    actor, headers = manager
    user, password = make_user("Employee")
    their_token = auth_header(login(user.email, password))

    response = client.post(f"{EMPLOYEES}/{user.employee_id}/deactivate", headers=headers)

    assert response.status_code == 200
    assert response.json()["user"]["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=their_token).status_code == 401
    relogin = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    assert relogin.status_code == 403
    [login_row] = audit_for("users", user.id, "user.deactivated")
    assert login_row.actor_user_id == actor.id
    assert login_row.after_data["is_active"] is False
    assert login_row.after_data["reason"] == "employee_deactivated"
    assert len(audit_for("employees", user.employee_id, "employee.deactivated")) == 1


def test_activating_employee_does_not_reactivate_the_login(client, manager, make_user):
    _, headers = manager
    user, _ = make_user("Employee")
    client.post(f"{EMPLOYEES}/{user.employee_id}/deactivate", headers=headers)

    response = client.post(f"{EMPLOYEES}/{user.employee_id}/activate", headers=headers)

    assert response.json()["status"] == "active"
    assert response.json()["user"]["is_active"] is False
    assert audit_for("users", user.id, "user.activated") == []


def test_already_inactive_login_gets_no_extra_audit_row(client, manager, make_user):
    _, headers = manager
    user, _ = make_user("Employee", is_active=False)

    client.post(f"{EMPLOYEES}/{user.employee_id}/deactivate", headers=headers)

    assert audit_for("users", user.id, "user.deactivated") == []


def test_cannot_deactivate_the_employee_linked_to_your_own_login(client, db, make_user, login):
    employee = Employee(employee_code="MGR-1", full_name="Manager Me")
    db.add(employee)
    db.commit()
    me, password = make_user("IT Manager", employee_id=employee.id)
    headers = auth_header(login(me.email, password))

    response = client.post(f"{EMPLOYEES}/{employee.id}/deactivate", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cannot_change_self"
    assert in_database(employee.id).status == "active"
    with SessionLocal() as fresh:
        assert fresh.get(User, me.id).is_active is True


def test_last_active_admin_protects_its_employee_record(db, make_user):
    employee = Employee(employee_code="ADM-1", full_name="Only Admin")
    db.add(employee)
    db.commit()
    make_user("Admin", employee_id=employee.id)
    from app.core.errors import AppError

    with pytest.raises(AppError) as exc:
        service.set_active(db, actor=None, employee=db.get(Employee, employee.id), active=False)

    assert exc.value.code == "last_admin"
    assert in_database(employee.id).status == "active"


def test_failed_audit_write_saves_nothing(db, monkeypatch):
    from app.modules.audit import service as audit

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit is down")

    monkeypatch.setattr(audit, "record", broken_record)
    with pytest.raises(RuntimeError):
        service.create_employee(db, data={"employee_code": "E-X", "full_name": "No Audit"})

    with SessionLocal() as fresh:
        assert fresh.scalars(select(Employee)).all() == []
