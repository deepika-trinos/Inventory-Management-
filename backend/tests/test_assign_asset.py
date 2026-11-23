"""Assign an asset (Slice 5.1: ASN-01 to ASN-04, EMP-05, BR-02, BR-03, BR-05, BR-11; owner's
answers A1, N1, N2, N3, N6, N9; decisions in decisions.md sections 26 and 27).

- POST /assets/{ref}/assign: only from Available; employee must exist and be active;
  assignment date today by default, earlier allowed, not in the future, not before the
  asset was created; optional expected return date on or after the assignment date.
- One transaction with audit assignment.created; a failure saves nothing.
- Only ONE open assignment per asset, also in the database (partial unique index).
- GET /assets: assigned_to filter and the current holder on each row (A1).
- Deactivating an employee who still holds assets is refused (N6).

Done-check (build plan): assigning an already-assigned asset, or assigning to an inactive
employee, is blocked."""

import threading
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.assets.models import Asset
from app.modules.assignments.models import Assignment
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditLog
from app.modules.employees import service as employees_service
from tests.test_asset_edit_retire import audit_rows, set_status, stored
from tests.test_asset_register import receive_laptops
from tests.test_purchases_api import (  # noqa: F401  (pytest fixtures used by name)
    data,
    error_code,
    manager,
    staff_headers,
)
from tests.test_receive_serialized import unit

ASSETS = "/api/v1/assets"
EMPLOYEES = "/api/v1/employees"


def today() -> date:
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()


@pytest.fixture
def laptops(client, manager, data):
    """AST-000001 (DL-1001) and AST-000002 (DL-1002), Available, received today."""
    _, headers = manager
    receive_laptops(client, headers, data, [unit("DL-1001"), unit("DL-1002")])
    return headers


@pytest.fixture
def people(db):
    """Asha Kumar (EMP-001, active, no login), Ravi Shah (EMP-002, active) and
    Old Timer (EMP-009, inactive)."""
    asha = employees_service.create_employee(db, data={"employee_code": "EMP-001", "full_name": "Asha Kumar"})
    ravi = employees_service.create_employee(db, data={"employee_code": "EMP-002", "full_name": "Ravi Shah"})
    old = employees_service.create_employee(db, data={"employee_code": "EMP-009", "full_name": "Old Timer"})
    employees_service.set_active(db, actor=None, employee=old, active=False)
    return {"asha": asha.id, "ravi": ravi.id, "old": old.id}


def assign(client, headers, code, employee_id, **body):
    return client.post(f"{ASSETS}/{code}/assign", headers=headers, json={"employee_id": employee_id, **body})


def assignments(code: str) -> list[Assignment]:
    with SessionLocal() as s:
        asset_id = s.scalars(select(Asset.id).where(Asset.asset_code == code)).one()
        rows = list(s.scalars(select(Assignment).where(Assignment.asset_id == asset_id).order_by(Assignment.id)))
        for r in rows:
            s.expunge(r)
        return rows


def created_days_ago(code: str, days: int) -> None:
    """Test-only shortcut: pretend the asset was added `days` days ago."""
    with SessionLocal() as s:
        s.execute(
            text("UPDATE assets SET created_at = created_at - make_interval(days => :d) WHERE asset_code = :c"),
            {"d": days, "c": code},
        )
        s.commit()


# ---- Assigning an Available asset ---------------------------------------------------------------
def test_assigning_an_available_asset_records_everything_and_audits_it(client, manager, laptops, people):
    user, headers = manager
    response = assign(client, headers, "AST-000001", people["asha"], expected_return_date=(today() + timedelta(days=30)).isoformat())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "assigned"
    current = body["current_assignment"]
    assert current["employee"] == {"id": people["asha"], "employee_code": "EMP-001", "full_name": "Asha Kumar", "status": "active"}
    assert current["assignment_date"] == today().isoformat()  # today by default (N1)
    assert current["expected_return_date"] == (today() + timedelta(days=30)).isoformat()
    assert current["assigned_by"]["id"] == user.id

    [row] = assignments("AST-000001")
    assert (row.employee_id, row.assigned_by_user_id, row.returned_at) == (people["asha"], user.id, None)
    assert stored("AST-000001").status == "assigned"

    [audit] = audit_rows("AST-000001", "assignment.created")
    assert audit.actor_user_id == user.id
    assert audit.before_data == {"status": "available"}
    assert audit.after_data == {
        "status": "assigned", "assignment_id": row.id, "employee_id": people["asha"], "employee_code": "EMP-001",
        "employee_name": "Asha Kumar", "assignment_date": today().isoformat(),
        "expected_return_date": (today() + timedelta(days=30)).isoformat(),
    }


def test_expected_return_date_is_optional(client, laptops, people):
    response = assign(client, laptops, "AST-000001", people["asha"])

    assert response.status_code == 200
    assert response.json()["current_assignment"]["expected_return_date"] is None


def test_an_employee_without_a_login_can_receive_an_asset(client, laptops, people, db):
    from app.modules.users.models import User

    assert db.scalar(select(User).where(User.employee_id == people["asha"])) is None
    assert assign(client, laptops, "AST-000001", people["asha"]).status_code == 200  # N3


def test_asset_page_and_history_show_the_assignment(client, laptops, people):
    assign(client, laptops, "AST-000001", people["asha"])

    asset = client.get(f"{ASSETS}/AST-000001", headers=laptops).json()
    history = client.get(f"{ASSETS}/AST-000001/history", headers=laptops).json()["items"]

    assert asset["current_assignment"]["employee"]["employee_code"] == "EMP-001"
    assert [e["action"] for e in history] == ["assignment.created", "asset.created"]
    assert history[0]["after"]["employee_name"] == "Asha Kumar"
    other = client.get(f"{ASSETS}/AST-000002", headers=laptops).json()
    assert other["current_assignment"] is None


# ---- Blocked asset statuses (BR-02, BR-03) ---------------------------------------------------------
def test_an_already_assigned_asset_cannot_be_assigned_again(client, laptops, people):
    assert assign(client, laptops, "AST-000001", people["asha"]).status_code == 200

    response = assign(client, laptops, "AST-000001", people["ravi"])

    assert response.status_code == 409
    assert error_code(response) == "asset_already_assigned"
    assert response.json()["error"]["details"] == {"status": "assigned"}
    [row] = assignments("AST-000001")
    assert row.employee_id == people["asha"]
    assert len(audit_rows("AST-000001", "assignment.created")) == 1


@pytest.mark.parametrize(
    "status, code",
    [
        ("under_maintenance", "asset_under_maintenance"),
        ("damaged", "asset_damaged"),
        ("retired", "asset_retired"),
    ],
)
def test_assets_that_are_not_available_cannot_be_assigned(client, laptops, people, status, code):
    set_status("AST-000001", status)

    response = assign(client, laptops, "AST-000001", people["asha"])

    assert response.status_code == 409
    assert error_code(response) == code
    assert response.json()["error"]["details"] == {"status": status}
    assert assignments("AST-000001") == []
    assert stored("AST-000001").status == status


# ---- Employee rules (EMP-05, BR-05, N3) ---------------------------------------------------------------
def test_an_inactive_employee_cannot_receive_an_asset(client, laptops, people):
    response = assign(client, laptops, "AST-000001", people["old"])

    assert response.status_code == 409
    assert error_code(response) == "employee_inactive"
    assert "Old Timer" in response.json()["error"]["message"]
    assert assignments("AST-000001") == []
    assert stored("AST-000001").status == "available"
    assert audit_rows("AST-000001", "assignment.created") == []


def test_an_unknown_employee_gives_404(client, laptops, people):
    response = assign(client, laptops, "AST-000001", 99999)

    assert response.status_code == 404
    assert error_code(response) == "employee_not_found"
    assert stored("AST-000001").status == "available"


# ---- Dates (N1, N2) -------------------------------------------------------------------------------------
def test_an_earlier_assignment_date_is_allowed(client, laptops, people):
    created_days_ago("AST-000001", 10)
    earlier = today() - timedelta(days=5)

    response = assign(client, laptops, "AST-000001", people["asha"], assignment_date=earlier.isoformat())

    assert response.status_code == 200
    assert response.json()["current_assignment"]["assignment_date"] == earlier.isoformat()


def test_the_day_the_asset_was_created_is_allowed(client, laptops, people):
    created_days_ago("AST-000001", 3)
    created_on = stored("AST-000001").created_at.astimezone(ZoneInfo(get_settings().app_timezone)).date()

    response = assign(client, laptops, "AST-000001", people["asha"], assignment_date=created_on.isoformat())

    assert response.status_code == 200


def test_a_future_assignment_date_is_refused(client, laptops, people):
    response = assign(client, laptops, "AST-000001", people["asha"], assignment_date=(today() + timedelta(days=1)).isoformat())

    assert response.status_code == 422
    assert error_code(response) == "assignment_date_in_future"
    assert assignments("AST-000001") == []


def test_an_assignment_date_before_the_asset_was_created_is_refused(client, laptops, people):
    response = assign(client, laptops, "AST-000001", people["asha"], assignment_date=(today() - timedelta(days=1)).isoformat())

    assert response.status_code == 422
    assert error_code(response) == "assignment_date_before_asset_created"
    assert response.json()["error"]["details"] == {"asset_created_on": today().isoformat()}
    assert stored("AST-000001").status == "available"


def test_expected_return_before_the_assignment_date_is_refused(client, laptops, people):
    created_days_ago("AST-000001", 10)
    response = assign(
        client, laptops, "AST-000001", people["asha"],
        assignment_date=(today() - timedelta(days=2)).isoformat(),
        expected_return_date=(today() - timedelta(days=3)).isoformat(),
    )

    assert response.status_code == 422
    assert error_code(response) == "invalid_expected_return_date"
    assert assignments("AST-000001") == []


def test_expected_return_on_the_assignment_date_is_allowed(client, laptops, people):
    response = assign(client, laptops, "AST-000001", people["asha"], expected_return_date=today().isoformat())

    assert response.status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {},  # employee missing
        {"employee_id": 0},
        {"employee_id": "abc"},
        {"employee_id": 1, "assignment_date": "not-a-date"},
        {"employee_id": 1, "status": "assigned"},  # unknown field
        {"employee_id": 1, "assigned_by_user_id": 1},
    ],
)
def test_bad_bodies_are_a_validation_error(client, laptops, people, body):
    response = client.post(f"{ASSETS}/AST-000001/assign", headers=laptops, json=body)

    assert response.status_code == 422
    assert error_code(response) == "validation_error"
    assert stored("AST-000001").status == "available"


# ---- One open assignment per asset -------------------------------------------------------------------
def test_database_allows_only_one_open_assignment_per_asset(db, manager, laptops, people):
    user, _ = manager
    asset_id = db.scalars(select(Asset.id).where(Asset.asset_code == "AST-000001")).one()
    for employee in ("asha", "ravi"):
        db.add(Assignment(asset_id=asset_id, employee_id=people[employee], assignment_date=today(), assigned_by_user_id=user.id))
    with pytest.raises(IntegrityError, match="uq_assignments_open_asset"):
        db.commit()
    db.rollback()


def test_database_refuses_expected_return_before_assignment(db, manager, laptops, people):
    user, _ = manager
    asset_id = db.scalars(select(Asset.id).where(Asset.asset_code == "AST-000001")).one()
    db.add(Assignment(
        asset_id=asset_id, employee_id=people["asha"], assignment_date=today(),
        expected_return_date=today() - timedelta(days=1), assigned_by_user_id=user.id,
    ))
    with pytest.raises(IntegrityError, match="expected_return_not_before_assignment"):
        db.commit()
    db.rollback()


def _assign_in_own_session(asset_code, user_id, employee_id, results, barrier):
    from app.core.errors import AppError
    from app.modules.assets import service as assets_service
    from app.modules.assignments import service
    from app.modules.users.models import User

    with SessionLocal() as session:
        actor = session.get(User, user_id)
        asset = assets_service.get_asset(session, asset_code)
        barrier.wait()
        try:
            service.assign_asset(session, actor=actor, asset=asset, employee_id=employee_id)
            results.append(("ok", employee_id))
        except AppError as error:
            results.append(("error", error.code))


def test_two_people_assigning_at_the_same_moment_only_one_wins(manager, laptops, people):
    user, _ = manager
    results: list = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_assign_in_own_session, args=("AST-000001", user.id, people[who], results, barrier))
        for who in ("asha", "ravi")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(kind for kind, _ in results) == ["error", "ok"]
    assert ("error", "asset_already_assigned") in results
    winner = next(value for kind, value in results if kind == "ok")
    [row] = assignments("AST-000001")
    assert row.employee_id == winner
    assert len(audit_rows("AST-000001", "assignment.created")) == 1


# ---- Nothing is saved when something fails ------------------------------------------------------------
def test_a_failing_audit_row_saves_nothing(client, laptops, people, monkeypatch):
    def broken_record(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(audit_service, "record", broken_record)
    with pytest.raises(RuntimeError):
        assign(client, laptops, "AST-000001", people["asha"])

    assert stored("AST-000001").status == "available"
    assert assignments("AST-000001") == []
    assert [r.action for r in audit_rows("AST-000001")] == ["asset.created"]


# ---- Employee deactivation while holding assets (N6) ----------------------------------------------------
def test_an_employee_holding_assets_cannot_be_deactivated(client, laptops, people):
    assign(client, laptops, "AST-000002", people["asha"])
    assign(client, laptops, "AST-000001", people["asha"])

    response = client.post(f"{EMPLOYEES}/{people['asha']}/deactivate", headers=laptops)

    assert response.status_code == 409
    assert error_code(response) == "employee_has_assets"
    error = response.json()["error"]
    assert "AST-000001, AST-000002" in error["message"]
    assert [a["asset_code"] for a in error["details"]["assets"]] == ["AST-000001", "AST-000002"]
    assert client.get(f"{EMPLOYEES}/{people['asha']}", headers=laptops).json()["status"] == "active"
    with SessionLocal() as s:
        assert s.scalar(select(AuditLog).where(AuditLog.action == "employee.deactivated", AuditLog.entity_id == str(people["asha"]))) is None


def test_an_employee_holding_nothing_can_still_be_deactivated(client, laptops, people):
    assign(client, laptops, "AST-000001", people["asha"])

    response = client.post(f"{EMPLOYEES}/{people['ravi']}/deactivate", headers=laptops)

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


def test_a_deactivation_blocked_by_assets_also_keeps_the_login_active(client, laptops, people, make_user):
    user, _ = make_user("Employee", employee_id=people["asha"])
    assign(client, laptops, "AST-000001", people["asha"])

    response = client.post(f"{EMPLOYEES}/{people['asha']}/deactivate", headers=laptops)

    assert error_code(response) == "employee_has_assets"
    from app.modules.users.models import User

    with SessionLocal() as s:
        assert s.get(User, user.id).is_active is True


# ---- Asset register: Assigned to column and filter (A1) -------------------------------------------------
def test_register_rows_show_the_current_holder(client, laptops, people):
    assign(client, laptops, "AST-000001", people["asha"])

    items = {r["asset_code"]: r for r in client.get(ASSETS, headers=laptops).json()["items"]}

    assert items["AST-000001"]["assigned_to"] == {
        "id": people["asha"], "employee_code": "EMP-001", "full_name": "Asha Kumar", "status": "active",
    }
    assert items["AST-000002"]["assigned_to"] is None


def test_assigned_to_filter_lists_only_that_employees_assets(client, laptops, people):
    assign(client, laptops, "AST-000001", people["asha"])
    assign(client, laptops, "AST-000002", people["ravi"])

    asha = client.get(ASSETS, headers=laptops, params={"assigned_to": people["asha"]}).json()
    nobody = client.get(ASSETS, headers=laptops, params={"assigned_to": people["old"]}).json()

    assert [r["asset_code"] for r in asha["items"]] == ["AST-000001"]
    assert asha["total"] == 1
    assert nobody == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_assigned_to_filter_works_for_an_inactive_employee(client, laptops, people, db):
    """An employee made inactive while holding an asset (e.g. by hand, before N6 existed)
    still shows in the filter's results (A1)."""
    assign(client, laptops, "AST-000001", people["ravi"])
    db.execute(text("UPDATE employees SET status = 'inactive' WHERE id = :i"), {"i": people["ravi"]})
    db.commit()

    rows = client.get(ASSETS, headers=laptops, params={"assigned_to": people["ravi"]}).json()["items"]

    assert [r["asset_code"] for r in rows] == ["AST-000001"]
    assert rows[0]["assigned_to"]["status"] == "inactive"


def test_assigned_to_filter_combines_with_the_other_filters(client, laptops, people):
    assign(client, laptops, "AST-000001", people["asha"])

    hit = client.get(ASSETS, headers=laptops, params={"assigned_to": people["asha"], "status": "assigned", "search": "DL-1001"})
    miss = client.get(ASSETS, headers=laptops, params={"assigned_to": people["asha"], "status": "available"})

    assert hit.json()["total"] == 1
    assert miss.json()["total"] == 0


@pytest.mark.parametrize("value, status, code", [(99999, 404, "employee_not_found"), ("abc", 422, "validation_error"), (0, 422, "validation_error")])
def test_bad_assigned_to_values(client, laptops, people, value, status, code):
    response = client.get(ASSETS, headers=laptops, params={"assigned_to": value})

    assert response.status_code == status
    assert error_code(response) == code


# ---- Roles ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_assign(client, staff_headers, laptops, people, role):
    _, headers = staff_headers(role)
    assert assign(client, headers, "AST-000001", people["asha"]).status_code == 200


def test_employee_role_cannot_assign(client, staff_headers, laptops, people):
    _, headers = staff_headers("Employee")

    response = assign(client, headers, "AST-000001", people["asha"])

    assert response.status_code == 403
    assert error_code(response) == "forbidden"
    assert stored("AST-000001").status == "available"


def test_assign_needs_login(client, laptops, people):
    assert client.post(f"{ASSETS}/AST-000001/assign", json={"employee_id": people["asha"]}).status_code == 401


@pytest.mark.parametrize("ref", ["AST-999999", "99999"])
def test_unknown_asset_gives_404(client, laptops, people, ref):
    assert error_code(assign(client, laptops, ref, people["asha"])) == "asset_not_found"


def test_assigning_by_numeric_id_and_lower_case_code_works(client, laptops, people):
    assert assign(client, laptops, "ast-000001", people["asha"]).status_code == 200
    assert assign(client, laptops, "2", people["ravi"]).status_code == 200
