"""Report a problem (Slice 6.1: MNT-01 to MNT-03; owner's answers Q9, Q10, Q13, N5, O1-O14;
decisions M1-M8 in decisions.md sections 31 and 32).

- POST /assets/{ref}/maintenance-requests (Admin, IT Manager): any asset except Retired; issue
  required (up to 1,000); optional priority low / medium / high; reported date today by default,
  earlier allowed, never future, never before the asset was created.
- POST /me/maintenance-requests (Employee): only an asset they hold now (otherwise 404
  asset_not_found); issue only; date today; no priority.
- Status Reported; number MNT-000001...; ONE open request per asset (also in the database).
- The asset's status never changes (Q9). One transaction with audit maintenance.reported.
- GET /assets/{ref}/maintenance-requests and GET /maintenance-requests (staff); My Assets rows
  show the open request.

Done-check (build plan): both an employee and the IT Manager can open a request."""

import threading
from datetime import timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.assets.models import Asset
from app.modules.audit import service as audit_service
from app.modules.maintenance.models import MaintenanceRequest
from tests.conftest import auth_header
from tests.test_asset_edit_retire import audit_rows, set_status, stored
from tests.test_assign_asset import (  # noqa: F401  (pytest fixtures used by name)
    ASSETS,
    assign,
    assignments,
    created_days_ago,
    laptops,
    people,
    today,
)
from tests.test_purchases_api import (  # noqa: F401  (pytest fixtures used by name)
    data,
    error_code,
    manager,
    staff_headers,
)
from tests.test_receive_serialized import unit

LIST = "/api/v1/maintenance-requests"
MINE = "/api/v1/me/maintenance-requests"
MY_ASSETS = "/api/v1/me/assignments"


def report(client, headers, code, issue="Screen flickers", **body):
    return client.post(f"{ASSETS}/{code}/maintenance-requests", headers=headers, json={"issue_description": issue, **body})


def my_report(client, headers, asset_id, issue="Battery drains fast", **body):
    return client.post(MINE, headers=headers, json={"asset_id": asset_id, "issue_description": issue, **body})


def requests_of(code: str) -> list[MaintenanceRequest]:
    with SessionLocal() as s:
        asset_id = s.scalars(select(Asset.id).where(Asset.asset_code == code)).one()
        rows = list(
            s.scalars(select(MaintenanceRequest).where(MaintenanceRequest.asset_id == asset_id).order_by(MaintenanceRequest.id))
            .unique()
        )
        for r in rows:
            s.expunge(r)
        return rows


def asset_id(code: str) -> int:
    return stored(code).id


def close_request(number: str, status: str = "completed") -> None:
    """Test-only shortcut to put a request in another status without the Slice 6.2 actions. Since
    migration 0016 the database requires each status's fields (who / when started, completed or
    cancelled), so they are filled in too, by the request's reporter, on its reported date. Since
    migration 0017 (Slice 6.3) a completed request awaiting inspection still blocks a new one, so the
    "completed" shortcut is also inspected (outcome Available)."""
    fields = {
        "in_progress": "started_date = reported_date, started_at = now(), started_by_user_id = reported_by_user_id",
        "completed": "started_date = reported_date, started_at = now(), started_by_user_id = reported_by_user_id,"
        " completion_date = reported_date, completed_at = now(), completed_by_user_id = reported_by_user_id,"
        " repair_notes = 'Test repair', inspection_outcome = 'available', inspection_date = reported_date,"
        " inspected_at = now(), inspected_by_user_id = reported_by_user_id",
        "cancelled": "cancelled_at = now(), cancelled_by_user_id = reported_by_user_id, cancel_reason = 'Test'",
    }[status]
    with SessionLocal() as s:
        s.execute(
            text(f"UPDATE maintenance_requests SET status = :s, {fields} WHERE request_number = :n"),
            {"s": status, "n": number},
        )
        s.commit()


@pytest.fixture
def asha_holds_one(client, laptops, people, make_user, login):
    """Asha Kumar (EMP-001) holds AST-000001 and has an Employee login; AST-000002 stays Available.
    Returns the Employee's headers."""
    assert assign(client, laptops, "AST-000001", people["asha"]).status_code == 200
    user, password = make_user("Employee", employee_id=people["asha"])
    return auth_header(login(user.email, password))


@pytest.fixture
def ravi_login(make_user, login, people):
    user, password = make_user("Employee", employee_id=people["ravi"])
    return auth_header(login(user.email, password))


# ---- Staff report (MNT-02) ------------------------------------------------------------------------------
def test_it_manager_reports_a_problem_and_everything_is_recorded(client, manager, laptops):
    user, headers = manager
    response = report(client, headers, "AST-000002", "  Screen flickers  ", priority="high")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["request_number"] == "MNT-000001"
    assert body["status"] == "reported"
    assert body["priority"] == "high"
    assert body["issue_description"] == "Screen flickers"  # trimmed
    assert body["reported_date"] == today().isoformat()  # today by default (O5)
    assert body["reported_by"] == {"id": user.id, "email": user.email, "role": "IT Manager"}
    assert body["asset"]["asset_code"] == "AST-000002"
    assert body["asset"]["status"] == "available"

    [row] = requests_of("AST-000002")
    assert (row.status, row.priority, row.reported_by_user_id) == ("reported", "high", user.id)


def test_priority_is_optional(client, laptops):
    response = report(client, laptops, "AST-000002")

    assert response.status_code == 201
    assert response.json()["priority"] is None


@pytest.mark.parametrize("priority", ["low", "medium", "high"])
def test_each_priority_is_accepted(client, laptops, priority):
    assert report(client, laptops, "AST-000002", priority=priority).json()["priority"] == priority


@pytest.mark.parametrize("status", ["available", "assigned", "damaged", "under_maintenance"])
def test_staff_can_report_on_any_status_except_retired(client, laptops, status):
    """O1; Under Maintenance is needed because a return as Under Maintenance opens no request (N5)."""
    set_status("AST-000002", status)

    response = report(client, laptops, "AST-000002")

    assert response.status_code == 201, response.text
    assert stored("AST-000002").status == status  # Q9: unchanged


def test_a_retired_asset_is_refused(client, laptops):
    set_status("AST-000002", "retired")

    response = report(client, laptops, "AST-000002")

    assert response.status_code == 409
    assert error_code(response) == "asset_retired"
    assert requests_of("AST-000002") == []


def test_reporting_never_changes_the_asset_or_its_assignment(client, laptops, people):
    """Q9: Under Maintenance starts only when work starts (Slice 6.2)."""
    assign(client, laptops, "AST-000001", people["asha"])
    [before] = assignments("AST-000001")

    assert report(client, laptops, "AST-000001").status_code == 201

    asset = client.get(f"{ASSETS}/AST-000001", headers=laptops).json()
    assert asset["status"] == "assigned"
    assert asset["current_assignment"]["employee"]["employee_code"] == "EMP-001"
    [after] = assignments("AST-000001")
    assert (after.id, after.returned_at, after.updated_at) == (before.id, None, before.updated_at)


def test_request_numbers_run_in_sequence(client, laptops):
    first = report(client, laptops, "AST-000001").json()["request_number"]
    second = report(client, laptops, "AST-000002").json()["request_number"]
    assert (first, second) == ("MNT-000001", "MNT-000002")


def test_the_asset_can_be_given_by_id_or_asset_id(client, laptops):
    assert report(client, laptops, str(asset_id("AST-000002"))).status_code == 201
    assert report(client, laptops, "ast-000001").status_code == 201


def test_unknown_asset_gives_404(client, laptops):
    response = report(client, laptops, "AST-999999")

    assert response.status_code == 404
    assert error_code(response) == "asset_not_found"


# ---- Issue text (O4) ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("issue", [None, "", "     "])
def test_the_issue_is_required(client, laptops, issue):
    response = client.post(f"{ASSETS}/AST-000002/maintenance-requests", headers=laptops, json={"issue_description": issue})

    assert response.status_code == 422
    assert error_code(response) == "invalid_issue_description"
    assert requests_of("AST-000002") == []


def test_the_issue_is_at_most_1000_characters(client, laptops):
    too_long = report(client, laptops, "AST-000002", "x" * 1001)
    assert too_long.status_code == 422
    assert error_code(too_long) == "invalid_issue_description"

    assert report(client, laptops, "AST-000002", "x" * 1000).status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        {"issue_description": "x", "priority": "urgent"},
        {"issue_description": "x", "priority": "High"},
        {"issue_description": "x", "status": "in_progress"},  # status only through actions (6.2)
        {"issue_description": "x", "reported_by_user_id": 1},
        {"issue_description": "x", "reported_date": "not-a-date"},
    ],
)
def test_bad_bodies_are_a_validation_error(client, laptops, body):
    response = client.post(f"{ASSETS}/AST-000002/maintenance-requests", headers=laptops, json=body)

    assert response.status_code == 422
    assert error_code(response) == "validation_error"


# ---- Reported date (O5) ---------------------------------------------------------------------------------------
def test_an_earlier_reported_date_is_allowed(client, laptops):
    created_days_ago("AST-000002", 10)
    on = today() - timedelta(days=3)

    response = report(client, laptops, "AST-000002", reported_date=on.isoformat())

    assert response.status_code == 201
    assert response.json()["reported_date"] == on.isoformat()


def test_a_future_reported_date_is_refused(client, laptops):
    response = report(client, laptops, "AST-000002", reported_date=(today() + timedelta(days=1)).isoformat())

    assert response.status_code == 422
    assert error_code(response) == "reported_date_in_future"


def test_a_reported_date_before_the_asset_was_created_is_refused(client, laptops):
    created_days_ago("AST-000002", 2)
    added = today() - timedelta(days=2)

    too_early = report(client, laptops, "AST-000002", reported_date=(added - timedelta(days=1)).isoformat())
    assert too_early.status_code == 422
    assert error_code(too_early) == "reported_date_before_asset_created"
    assert too_early.json()["error"]["details"] == {"asset_created_on": added.isoformat()}

    assert report(client, laptops, "AST-000002", reported_date=added.isoformat()).status_code == 201


# ---- One open request per asset (O2) ---------------------------------------------------------------------------
def test_a_second_open_request_is_refused_and_names_the_first(client, laptops):
    report(client, laptops, "AST-000002")

    again = report(client, laptops, "AST-000002", "Another problem")

    assert again.status_code == 409
    assert error_code(again) == "maintenance_request_open"
    assert again.json()["error"]["details"] == {"request_number": "MNT-000001"}
    assert len(requests_of("AST-000002")) == 1


def test_an_in_progress_request_also_blocks_a_new_one(client, laptops):
    report(client, laptops, "AST-000002")
    close_request("MNT-000001", "in_progress")

    assert error_code(report(client, laptops, "AST-000002")) == "maintenance_request_open"


@pytest.mark.parametrize("status", ["completed", "cancelled"])
def test_a_closed_request_does_not_block_a_new_one(client, laptops, status):
    report(client, laptops, "AST-000002")
    close_request("MNT-000001", status)

    response = report(client, laptops, "AST-000002")

    assert response.status_code == 201
    assert response.json()["request_number"] == "MNT-000002"


def test_the_database_allows_only_one_open_request_per_asset(laptops, manager):
    user, _ = manager
    with SessionLocal() as s:
        aid = asset_id("AST-000002")
        s.add(MaintenanceRequest(asset_id=aid, issue_description="a", reported_date=today(), reported_by_user_id=user.id))
        s.commit()
        s.add(MaintenanceRequest(asset_id=aid, issue_description="b", reported_date=today(), reported_by_user_id=user.id))
        with pytest.raises(IntegrityError, match="uq_maintenance_requests_open_asset"):
            s.commit()


def test_the_database_refuses_an_unknown_status_or_priority(laptops, manager):
    user, _ = manager
    for field in ({"status": "open"}, {"priority": "urgent"}):
        with SessionLocal() as s:
            s.add(MaintenanceRequest(
                asset_id=asset_id("AST-000002"), issue_description="a", reported_date=today(),
                reported_by_user_id=user.id, **field,
            ))
            with pytest.raises(IntegrityError):
                s.commit()


# ---- Audit (BR-13, O14) ------------------------------------------------------------------------------------------
def test_the_report_writes_one_audit_row_on_the_asset(client, manager, laptops):
    user, headers = manager
    report(client, headers, "AST-000002", "Screen flickers", priority="high")

    [row] = audit_rows("AST-000002", "maintenance.reported")
    [request] = requests_of("AST-000002")
    assert row.actor_user_id == user.id
    assert row.before_data is None
    assert row.after_data == {
        "request_id": request.id, "request_number": "MNT-000001", "issue_description": "Screen flickers",
        "priority": "high", "reported_date": today().isoformat(), "status": "reported",
        "reported_by_role": "IT Manager",
    }
    history = client.get(f"{ASSETS}/AST-000002/history", headers=headers).json()["items"]
    assert history[0]["action"] == "maintenance.reported"


def test_a_failing_audit_row_saves_nothing(client, laptops, monkeypatch):
    def broken_record(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(audit_service, "record", broken_record)
    with pytest.raises(RuntimeError):
        report(client, laptops, "AST-000002")

    assert requests_of("AST-000002") == []
    assert audit_rows("AST-000002", "maintenance.reported") == []


# ---- Two reports at the same moment (M5) ----------------------------------------------------------------------------
def _report_in_own_session(code, user_id, issue, results, barrier):
    from app.core.errors import AppError
    from app.modules.assets import service as assets_service
    from app.modules.maintenance import service
    from app.modules.users.models import User

    with SessionLocal() as session:
        actor = session.get(User, user_id)
        asset = assets_service.get_asset(session, code)
        barrier.wait()
        try:
            service.report_problem(session, actor=actor, asset=asset, issue_description=issue)
            results.append(("ok", issue))
        except AppError as error:
            results.append(("error", error.code))


def test_two_reports_at_the_same_moment_only_one_wins(manager, laptops):
    user, _ = manager
    results: list = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_report_in_own_session, args=("AST-000002", user.id, issue, results, barrier))
        for issue in ("first", "second")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(kind for kind, _ in results) == ["error", "ok"]
    assert ("error", "maintenance_request_open") in results
    assert len(requests_of("AST-000002")) == 1
    assert len(audit_rows("AST-000002", "maintenance.reported")) == 1


# ---- Employee report (MNT-01) ---------------------------------------------------------------------------------------
def test_an_employee_reports_a_problem_with_their_own_asset(client, asha_holds_one):
    response = my_report(client, asha_holds_one, asset_id("AST-000001"), "  Battery drains fast  ")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body == {
        "request_number": "MNT-000001",
        "asset": {
            "id": asset_id("AST-000001"), "asset_code": "AST-000001", "name": body["asset"]["name"],
            "serial_number": "DL-1001", "status": "assigned",
        },
        "issue_description": "Battery drains fast",
        "status": "reported",
        "reported_date": today().isoformat(),
    }
    [row] = requests_of("AST-000001")
    assert row.priority is None  # Q10: set by the IT Manager only
    assert stored("AST-000001").status == "assigned"  # Q9
    [audit] = audit_rows("AST-000001", "maintenance.reported")
    assert audit.after_data["reported_by_role"] == "Employee"


def test_the_it_manager_sees_the_employee_report(client, laptops, asha_holds_one):
    my_report(client, asha_holds_one, asset_id("AST-000001"))

    [row] = client.get(f"{ASSETS}/AST-000001/maintenance-requests", headers=laptops).json()
    assert (row["request_number"], row["status"], row["reported_by"]["role"]) == ("MNT-000001", "reported", "Employee")
    assert client.get(LIST, headers=laptops).json()["total"] == 1


@pytest.mark.parametrize(
    "extra",
    [{"priority": "high"}, {"priority": None}, {"reported_date": "2026-01-01"}, {"status": "reported"}],
)
def test_an_employee_cannot_send_a_priority_a_date_or_anything_else(client, asha_holds_one, extra):
    response = my_report(client, asha_holds_one, asset_id("AST-000001"), **extra)

    assert response.status_code == 422
    assert error_code(response) == "validation_error"
    assert requests_of("AST-000001") == []


def test_an_employee_cannot_report_someone_elses_asset(client, laptops, people, asha_holds_one, ravi_login):
    """O7: the same answer as for a missing asset, so other people's assets cannot be discovered."""
    response = my_report(client, ravi_login, asset_id("AST-000001"))

    assert response.status_code == 404
    assert error_code(response) == "asset_not_found"
    assert requests_of("AST-000001") == []


def test_an_employee_cannot_report_an_asset_nobody_holds(client, asha_holds_one):
    response = my_report(client, asha_holds_one, asset_id("AST-000002"))  # Available, not hers

    assert response.status_code == 404
    assert error_code(response) == "asset_not_found"


def test_an_unknown_asset_gives_the_same_404(client, asha_holds_one):
    response = my_report(client, asha_holds_one, 999_999)

    assert response.status_code == 404
    assert error_code(response) == "asset_not_found"


def test_an_employee_cannot_report_after_returning_the_asset(client, laptops, asha_holds_one):
    """O6."""
    returned = client.post(f"{ASSETS}/AST-000001/return", headers=laptops, json={"inspection_outcome": "available"})
    assert returned.status_code == 200

    response = my_report(client, asha_holds_one, asset_id("AST-000001"))

    assert response.status_code == 404
    assert error_code(response) == "asset_not_found"


@pytest.mark.parametrize("issue", [None, "", "   ", "x" * 1001])
def test_the_employee_issue_has_the_same_rules(client, asha_holds_one, issue):
    response = client.post(MINE, headers=asha_holds_one, json={"asset_id": asset_id("AST-000001"), "issue_description": issue})

    assert response.status_code == 422
    assert error_code(response) == "invalid_issue_description"


def test_an_employee_report_is_refused_while_a_request_is_open(client, laptops, asha_holds_one):
    report(client, laptops, "AST-000001", priority="low")  # the IT Manager opened one first

    response = my_report(client, asha_holds_one, asset_id("AST-000001"))

    assert response.status_code == 409
    assert error_code(response) == "maintenance_request_open"
    assert response.json()["error"]["details"] == {"request_number": "MNT-000001"}


def test_staff_cannot_use_the_employee_endpoint(client, staff_headers, laptops):
    for role in ("Admin", "IT Manager"):
        _, headers = staff_headers(role)
        assert my_report(client, headers, asset_id("AST-000001")).status_code == 403


def test_a_login_without_an_employee_record_gives_404(client, laptops, make_user, login, db):
    user, password = make_user("Employee")
    db.execute(text("UPDATE users SET employee_id = NULL WHERE id = :i"), {"i": user.id})
    db.commit()
    headers = auth_header(login(user.email, password))

    response = my_report(client, headers, asset_id("AST-000001"))

    assert response.status_code == 404
    assert error_code(response) == "employee_not_linked"


# ---- My Assets shows the open request (M7) ---------------------------------------------------------------------------
def test_my_assets_shows_the_open_request_on_the_held_asset(client, asha_holds_one):
    assert client.get(MY_ASSETS, headers=asha_holds_one).json()["current"][0]["open_request"] is None

    my_report(client, asha_holds_one, asset_id("AST-000001"))

    [row] = client.get(MY_ASSETS, headers=asha_holds_one).json()["current"]
    assert row["open_request"] == {"request_number": "MNT-000001", "status": "reported", "reported_date": today().isoformat()}


def test_my_assets_no_longer_shows_a_closed_request(client, asha_holds_one):
    my_report(client, asha_holds_one, asset_id("AST-000001"))
    close_request("MNT-000001", "cancelled")

    [row] = client.get(MY_ASSETS, headers=asha_holds_one).json()["current"]
    assert row["open_request"] is None


# ---- Reading (M7, O12) -----------------------------------------------------------------------------------------------
def test_an_assets_requests_are_newest_first(client, laptops):
    report(client, laptops, "AST-000002", "first")
    close_request("MNT-000001")
    report(client, laptops, "AST-000002", "second", priority="medium")

    rows = client.get(f"{ASSETS}/AST-000002/maintenance-requests", headers=laptops).json()

    assert [(r["request_number"], r["status"], r["priority"]) for r in rows] == [
        ("MNT-000002", "reported", "medium"), ("MNT-000001", "completed", None),
    ]
    assert client.get(f"{ASSETS}/AST-000001/maintenance-requests", headers=laptops).json() == []


def test_unknown_asset_requests_give_404(client, laptops):
    response = client.get(f"{ASSETS}/AST-999999/maintenance-requests", headers=laptops)
    assert error_code(response) == "asset_not_found"


def test_the_list_is_newest_first_searchable_filterable_and_sortable(client, laptops, data):
    from tests.test_asset_register import receive_laptops

    receive_laptops(client, laptops, data, [unit("HP-77")], reference="INV-2026-0099")  # AST-000003
    report(client, laptops, "AST-000001", "one", priority="high")
    report(client, laptops, "AST-000002", "two", priority="low")
    report(client, laptops, "AST-000003", "three")
    close_request("MNT-000002", "cancelled")

    def numbers(**params):
        body = client.get(LIST, headers=laptops, params=params).json()
        return [r["request_number"] for r in body["items"]]

    assert numbers() == ["MNT-000003", "MNT-000002", "MNT-000001"]
    assert numbers(status="reported") == ["MNT-000003", "MNT-000001"]
    assert numbers(search="hp-7") == ["MNT-000003"]  # serial number, any case
    assert numbers(search="ast-000002") == ["MNT-000002"]
    assert numbers(search="mnt-000001") == ["MNT-000001"]
    assert numbers(sort="priority") == ["MNT-000003", "MNT-000002", "MNT-000001"]  # none, low, high
    assert numbers(sort="-priority") == ["MNT-000001", "MNT-000002", "MNT-000003"]
    assert numbers(sort="asset_code", page_size=1, page=2) == ["MNT-000002"]


def test_the_list_refuses_an_unknown_status_or_sort(client, laptops):
    assert error_code(client.get(LIST, headers=laptops, params={"status": "open"})) == "validation_error"
    assert error_code(client.get(LIST, headers=laptops, params={"sort": "issue_description"})) == "invalid_sort"


# ---- Roles (Q13, PRD 4.1) ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_report_and_read(client, staff_headers, laptops, role):
    _, headers = staff_headers(role)

    response = report(client, headers, "AST-000002")

    assert response.status_code == 201
    assert response.json()["reported_by"]["role"] == role
    assert client.get(LIST, headers=headers).status_code == 200
    assert client.get(f"{ASSETS}/AST-000002/maintenance-requests", headers=headers).status_code == 200


def test_employee_role_cannot_use_the_staff_endpoints(client, laptops, asha_holds_one):
    assert report(client, asha_holds_one, "AST-000001").status_code == 403
    assert client.get(LIST, headers=asha_holds_one).status_code == 403
    assert client.get(f"{ASSETS}/AST-000001/maintenance-requests", headers=asha_holds_one).status_code == 403
    assert requests_of("AST-000001") == []


def test_every_endpoint_needs_a_login(client, laptops):
    assert report(client, {}, "AST-000002").status_code == 401
    assert my_report(client, {}, asset_id("AST-000002")).status_code == 401
    assert client.get(LIST).status_code == 401
    assert client.get(f"{ASSETS}/AST-000002/maintenance-requests").status_code == 401
