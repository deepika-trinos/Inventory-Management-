"""User management API (Slice 1.6, AUTH-05, BR-12, BR-13)."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal, utc_now
from app.core.errors import AppError
from app.modules.audit.models import AuditLog
from app.modules.employees.models import Employee
from app.modules.users import service
from app.modules.users.models import User
from tests.conftest import auth_header

USERS = "/api/v1/users"
TEMP_PASSWORD = "temporary-pass-123"


@pytest.fixture
def admin_session(make_user, login):
    """An Admin user and their token."""
    admin, password = make_user("Admin")
    return admin, auth_header(login(admin.email, password))


def audit_for(user_id: int, action: str) -> list[AuditLog]:
    with SessionLocal() as fresh:
        return list(
            fresh.scalars(
                select(AuditLog)
                .where(AuditLog.entity_type == "users", AuditLog.entity_id == str(user_id), AuditLog.action == action)
                .order_by(AuditLog.id)
            ).all()
        )


# ---- Only Admins ------------------------------------------------------------------
ENDPOINTS = [
    ("get", USERS, None),
    ("post", USERS, {"email": "x@example.com", "password": TEMP_PASSWORD, "role": "Employee"}),
    ("get", f"{USERS}/1", None),
    ("patch", f"{USERS}/1", {"email": "y@example.com"}),
    ("patch", f"{USERS}/1/role", {"role": "Admin"}),
    ("post", f"{USERS}/1/activate", None),
    ("post", f"{USERS}/1/deactivate", None),
]


@pytest.mark.parametrize("role", ["IT Manager", "Employee"])
@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_non_admins_get_403_on_every_users_endpoint(client, make_user, login, role, method, url, body):
    user, password = make_user(role)
    headers = auth_header(login(user.email, password))

    response = client.request(method, url, json=body, headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_users_endpoints_need_login(client, method, url, body):
    assert client.request(method, url, json=body).status_code == 401


# ---- Create -------------------------------------------------------------------------
def test_admin_creates_it_manager_who_can_log_in(client, admin_session):
    admin, headers = admin_session

    response = client.post(
        USERS, headers=headers,
        json={"email": "New.Manager@Example.com", "password": TEMP_PASSWORD, "role": "IT Manager"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.manager@example.com"
    assert body["role"]["name"] == "IT Manager"
    assert body["is_active"] is True
    login = client.post("/api/v1/auth/login", json={"email": body["email"], "password": TEMP_PASSWORD})
    assert login.status_code == 200

    [row] = audit_for(body["id"], "user.created")
    assert row.actor_user_id == admin.id
    assert row.after_data["role"] == "IT Manager"
    assert row.after_data["is_active"] is True
    assert "password" not in str(row.after_data).lower()


def test_duplicate_email_is_rejected_ignoring_case(client, admin_session, make_user):
    _, headers = admin_session
    make_user(email="taken@example.com")

    response = client.post(
        USERS, headers=headers, json={"email": "TAKEN@example.com", "password": TEMP_PASSWORD, "role": "Employee"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"email": "a@example.com", "password": "short", "role": "Employee"}, "weak_password"),
        ({"email": "not-an-email", "password": TEMP_PASSWORD, "role": "Employee"}, "invalid_email"),
        ({"email": "a@example.com", "password": TEMP_PASSWORD, "role": "Boss"}, "validation_error"),
        ({"email": "a@example.com", "role": "Employee"}, "validation_error"),
    ],
)
def test_create_user_validation(client, admin_session, body, code):
    _, headers = admin_session

    response = client.post(USERS, headers=headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_create_user_with_employee_link(client, admin_session, db):
    _, headers = admin_session
    employee = Employee(employee_code="EMP-100", full_name="Ravi Shah")
    db.add(employee)
    db.commit()
    body = {"email": "ravi@example.com", "password": TEMP_PASSWORD, "role": "Employee", "employee_id": employee.id}

    first = client.post(USERS, headers=headers, json=body)
    second = client.post(USERS, headers=headers, json={**body, "email": "ravi2@example.com"})
    missing = client.post(USERS, headers=headers, json={**body, "email": "x@example.com", "employee_id": 9999})

    assert first.status_code == 201
    assert first.json()["employee"]["full_name"] == "Ravi Shah"
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "employee_has_login"
    assert missing.status_code == 404


# ---- List, get, update -----------------------------------------------------------------
def test_list_search_filter_and_paging(client, admin_session, make_user, db):
    _, headers = admin_session
    make_user("IT Manager", email="mgr@example.com")
    inactive, _ = make_user("Employee", email="gone@example.com", is_active=False)
    employee = Employee(employee_code="EMP-7", full_name="Meera Iyer")
    db.add(employee)
    db.commit()
    service.create_user(db, email="m.iyer@example.com", password=TEMP_PASSWORD, role_name="Employee",
                        employee_id=employee.id)

    everyone = client.get(USERS, headers=headers).json()
    by_name = client.get(USERS, headers=headers, params={"search": "meera"}).json()
    managers = client.get(USERS, headers=headers, params={"role": "IT Manager"}).json()
    inactive_only = client.get(USERS, headers=headers, params={"is_active": "false"}).json()
    page = client.get(USERS, headers=headers, params={"page_size": 2, "page": 2, "sort": "email"}).json()

    assert everyone["total"] == 4
    assert [u["email"] for u in by_name["items"]] == ["m.iyer@example.com"]
    assert [u["email"] for u in managers["items"]] == ["mgr@example.com"]
    assert [u["id"] for u in inactive_only["items"]] == [inactive.id]
    assert page["page"] == 2 and page["page_size"] == 2 and len(page["items"]) == 2


def test_get_unknown_user_is_404(client, admin_session):
    _, headers = admin_session

    response = client.get(f"{USERS}/99999", headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"


def test_update_email_writes_audit_and_blocks_duplicates(client, admin_session, make_user):
    admin, headers = admin_session
    user, _ = make_user(email="old@example.com")
    make_user(email="other@example.com")

    ok = client.patch(f"{USERS}/{user.id}", headers=headers, json={"email": "New@Example.com"})
    clash = client.patch(f"{USERS}/{user.id}", headers=headers, json={"email": "OTHER@example.com"})

    assert ok.status_code == 200
    assert ok.json()["email"] == "new@example.com"
    assert clash.status_code == 409
    [row] = audit_for(user.id, "user.updated")
    assert row.actor_user_id == admin.id
    assert (row.before_data["email"], row.after_data["email"]) == ("old@example.com", "new@example.com")


# ---- Role change ---------------------------------------------------------------------
def test_role_change_writes_audit_row_with_admin_id_and_time(client, admin_session, make_user):
    admin, headers = admin_session
    user, _ = make_user("Employee")
    started = utc_now()

    response = client.patch(f"{USERS}/{user.id}/role", headers=headers, json={"role": "IT Manager"})

    assert response.status_code == 200
    assert response.json()["role"]["name"] == "IT Manager"
    [row] = audit_for(user.id, "user.role_changed")
    assert row.actor_user_id == admin.id
    assert row.created_at.utcoffset() == timedelta(0)
    assert started - timedelta(seconds=5) <= row.created_at <= utc_now() + timedelta(seconds=5)
    assert (row.before_data["role"], row.after_data["role"]) == ("Employee", "IT Manager")
    assert "is_active" in row.after_data


def test_admin_cannot_remove_their_own_admin_role(client, admin_session, make_user):
    admin, headers = admin_session
    make_user("Admin")  # another Admin exists, still not allowed

    response = client.patch(f"{USERS}/{admin.id}/role", headers=headers, json={"role": "Employee"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cannot_change_self"
    assert audit_for(admin.id, "user.role_changed") == []


def test_admin_can_demote_another_admin_when_one_remains(client, admin_session, make_user):
    _, headers = admin_session
    other_admin, _ = make_user("Admin")

    response = client.patch(f"{USERS}/{other_admin.id}/role", headers=headers, json={"role": "IT Manager"})

    assert response.status_code == 200


# ---- Activate / deactivate -------------------------------------------------------------
def test_deactivated_user_cannot_log_in_and_their_token_stops_working(client, admin_session, make_user, login):
    admin, headers = admin_session
    user, password = make_user("IT Manager")
    their_token = auth_header(login(user.email, password))
    assert client.get("/api/v1/auth/me", headers=their_token).status_code == 200

    response = client.post(f"{USERS}/{user.id}/deactivate", headers=headers)

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=their_token).status_code == 401
    relogin = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    assert relogin.status_code == 403
    assert relogin.json()["error"]["code"] == "account_inactive"
    [row] = audit_for(user.id, "user.deactivated")
    assert row.actor_user_id == admin.id
    assert (row.before_data["is_active"], row.after_data["is_active"]) == (True, False)


def test_reactivated_user_can_log_in_again(client, admin_session, make_user):
    _, headers = admin_session
    user, password = make_user(is_active=False)

    response = client.post(f"{USERS}/{user.id}/activate", headers=headers)

    assert response.json()["is_active"] is True
    assert client.post("/api/v1/auth/login", json={"email": user.email, "password": password}).status_code == 200
    assert len(audit_for(user.id, "user.activated")) == 1


def test_admin_cannot_deactivate_themselves(client, admin_session):
    admin, headers = admin_session

    response = client.post(f"{USERS}/{admin.id}/deactivate", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cannot_change_self"


def test_deactivating_an_inactive_user_changes_nothing(client, admin_session, make_user):
    _, headers = admin_session
    user, _ = make_user(is_active=False)

    response = client.post(f"{USERS}/{user.id}/deactivate", headers=headers)

    assert response.status_code == 200
    assert audit_for(user.id, "user.deactivated") == []


# ---- Last active Admin -----------------------------------------------------------------
# Through the API, the acting Admin is always active, so the "self" rule normally
# triggers first. The last-Admin rule is the safety net underneath it (for example
# for system actions or two Admins acting at the same moment), so it is tested on
# the service directly.
@pytest.mark.parametrize("action", ["demote", "deactivate"])
def test_last_active_admin_cannot_be_demoted_or_deactivated(db, make_user, action):
    only_admin, _ = make_user("Admin")
    make_user("Admin", is_active=False)  # an inactive Admin does not count
    system_actor = None

    with pytest.raises(AppError) as exc:
        if action == "demote":
            service.change_role(db, actor=system_actor, user=only_admin, new_role_name="Employee")
        else:
            service.set_active(db, actor=system_actor, user=only_admin, active=False)

    assert exc.value.code == "last_admin"
    with SessionLocal() as fresh:
        saved = fresh.get(User, only_admin.id)
        assert saved.role.name == "Admin" and saved.is_active is True


def test_second_admin_can_be_deactivated_but_then_the_first_is_protected(client, admin_session, make_user, db):
    admin, headers = admin_session
    other_admin, _ = make_user("Admin")

    assert client.post(f"{USERS}/{other_admin.id}/deactivate", headers=headers).status_code == 200

    with pytest.raises(AppError) as exc:
        service.set_active(db, actor=None, user=db.get(User, admin.id), active=False)
    assert exc.value.code == "last_admin"


# ---- Never leak passwords -----------------------------------------------------------------
def test_users_responses_never_contain_password_data(client, admin_session, make_user):
    _, headers = admin_session
    user, _ = make_user()

    responses = [
        client.get(USERS, headers=headers),
        client.get(f"{USERS}/{user.id}", headers=headers),
        client.post(USERS, headers=headers, json={"email": "p@example.com", "password": TEMP_PASSWORD, "role": "IT Manager"}),
        client.patch(f"{USERS}/{user.id}/role", headers=headers, json={"role": "IT Manager"}),
    ]

    for response in responses:
        assert response.status_code in (200, 201)
        assert "password" not in response.text
        assert "$argon2" not in response.text
        assert TEMP_PASSWORD not in response.text
