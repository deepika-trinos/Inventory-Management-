"""Login, current user, logout and role checks (Slice 1.3)."""

from datetime import timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import utc_now
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import Role, User
from tests.conftest import auth_header

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"
ADMIN_PING = "/api/v1/admin/ping"


# ---- Login ---------------------------------------------------------------------
def test_login_success_returns_bearer_token(client, make_user, db):
    user, password = make_user("Admin")

    response = client.post(LOGIN, json={"email": user.email, "password": password})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60
    assert body["access_token"].count(".") == 2  # header.payload.signature
    db.refresh(user)
    assert user.last_login_at is not None


def test_login_email_is_not_case_sensitive(client, make_user):
    user, password = make_user(email="asha.k@example.com")

    response = client.post(LOGIN, json={"email": "  Asha.K@Example.COM ", "password": password})

    assert response.status_code == 200


def test_wrong_password_and_unknown_email_get_the_same_error(client, make_user):
    user, _ = make_user()

    wrong_password = client.post(LOGIN, json={"email": user.email, "password": "wrong-password"})
    unknown_email = client.post(LOGIN, json={"email": "nobody@example.com", "password": "x"})

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == {
        "error": {
            "code": "invalid_credentials",
            "message": "Incorrect email or password.",
            "details": None,
        }
    }


def test_inactive_user_cannot_log_in(client, make_user):
    user, password = make_user(is_active=False)

    response = client.post(LOGIN, json={"email": user.email, "password": password})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_inactive"
    assert "access_token" not in response.text


def test_inactive_user_with_wrong_password_gets_the_generic_error(client, make_user):
    user, _ = make_user(is_active=False)

    response = client.post(LOGIN, json={"email": user.email, "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_validation_error_uses_standard_format_and_hides_input(client):
    response = client.post(LOGIN, json={"email": "a@b.co", "password": ""})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["field"] == "body.password"
    assert "input" not in response.text


# ---- /me and tokens ------------------------------------------------------------
def test_me_without_token_is_401(client):
    response = client.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_returns_user_role_and_no_password_hash(client, make_user, login):
    user, password = make_user("IT Manager")
    token = login(user.email, password)

    response = client.get(ME, headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == user.email
    assert body["role"]["name"] == "IT Manager"
    assert body["employee"] is None
    assert body["is_active"] is True
    assert "password_hash" not in body
    assert body["created_at"].endswith("Z") or body["created_at"].endswith("+00:00")


@pytest.mark.parametrize("bad_token", ["not-a-token", "a.b.c", ""])
def test_garbage_token_is_401(client, bad_token):
    response = client.get(ME, headers={"Authorization": f"Bearer {bad_token}"})

    assert response.status_code == 401


def test_expired_token_is_401(client, make_user):
    user, _ = make_user()
    settings = get_settings()
    past = utc_now() - timedelta(hours=2)
    expired = jwt.encode(
        {"sub": str(user.id), "type": "access", "iat": past, "exp": past + timedelta(minutes=30)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    response = client.get(ME, headers=auth_header(expired))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_token_signed_with_another_secret_is_401(client, make_user):
    user, _ = make_user("Admin")
    now = utc_now()
    forged = jwt.encode(
        {"sub": str(user.id), "type": "access", "iat": now, "exp": now + timedelta(minutes=30)},
        "attacker-secret-attacker-secret-attacker-secret",
        algorithm="HS256",
    )

    response = client.get(ADMIN_PING, headers=auth_header(forged))

    assert response.status_code == 401


def test_deactivated_users_existing_token_is_rejected(client, make_user, login, db):
    user, password = make_user("Admin")
    token = login(user.email, password)
    assert client.get(ME, headers=auth_header(token)).status_code == 200

    user.is_active = False
    db.commit()

    response = client.get(ME, headers=auth_header(token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


# ---- Role checks ---------------------------------------------------------------
def test_admin_can_call_admin_endpoint(client, make_user, login):
    user, password = make_user("Admin")

    response = client.get(ADMIN_PING, headers=auth_header(login(user.email, password)))

    assert response.status_code == 200
    assert response.json() == {"message": "pong", "email": user.email, "role": "Admin"}


@pytest.mark.parametrize("role", ["Employee", "IT Manager"])
def test_non_admin_gets_403_on_admin_endpoint(client, make_user, login, role):
    user, password = make_user(role)

    response = client.get(ADMIN_PING, headers=auth_header(login(user.email, password)))

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "forbidden"
    assert error["details"] == {"your_role": role, "allowed_roles": ["Admin"]}


def test_admin_endpoint_without_token_is_401(client):
    assert client.get(ADMIN_PING).status_code == 401


def test_role_change_takes_effect_on_next_request(client, make_user, login, db):
    user, password = make_user("Admin")
    token = login(user.email, password)
    assert client.get(ADMIN_PING, headers=auth_header(token)).status_code == 200

    user.role = db.scalar(select(Role).where(Role.name == "Employee"))
    db.commit()

    assert client.get(ADMIN_PING, headers=auth_header(token)).status_code == 403


def test_require_roles_rejects_unknown_role_names():
    with pytest.raises(ValueError):
        require_roles("admin")  # wrong case: a typo must fail loudly


# ---- Logout --------------------------------------------------------------------
def test_logout_returns_204_with_token_and_401_without(client, make_user, login):
    user, password = make_user()
    token = login(user.email, password)

    assert client.post(LOGOUT, headers=auth_header(token)).status_code == 204
    assert client.post(LOGOUT).status_code == 401


# ---- password_hash never leaves the server -------------------------------------
def test_password_hash_never_appears_in_any_response(client, make_user, login, db):
    admin, admin_pw = make_user("Admin")
    employee, employee_pw = make_user("Employee")
    inactive, inactive_pw = make_user(is_active=False)
    admin_token = login(admin.email, admin_pw)
    employee_token = login(employee.email, employee_pw)
    stored_hashes = [u.password_hash for u in db.scalars(select(User)).all()]

    responses = [
        client.post(LOGIN, json={"email": admin.email, "password": admin_pw}),
        client.post(LOGIN, json={"email": admin.email, "password": "wrong"}),
        client.post(LOGIN, json={"email": inactive.email, "password": inactive_pw}),
        client.post(LOGIN, json={"email": "x"}),
        client.get(ME, headers=auth_header(admin_token)),
        client.get(ME, headers=auth_header(employee_token)),
        client.get(ME),
        client.get(ADMIN_PING, headers=auth_header(admin_token)),
        client.get(ADMIN_PING, headers=auth_header(employee_token)),
        client.post(LOGOUT, headers=auth_header(admin_token)),
        client.get("/openapi.json"),
    ]

    for response in responses:
        assert "password_hash" not in response.text, response.request.url
        assert "$argon2" not in response.text, response.request.url
        for stored in stored_hashes:
            assert stored not in response.text
