"""Repair progress (Slice 6.2: MNT-04 to MNT-07, BR-05, BR-13; owner's answers Q9, S1-S14; decisions
U1-U9 in decisions.md sections 33 and 34).

- Reported -> In Progress (start): asset becomes Under Maintenance; refused while Assigned (S1) or Retired.
- In Progress -> Completed: completion date and repair notes required; asset stays Under Maintenance.
- Reported / In Progress -> Cancelled: required reason; from In Progress the asset stays Under Maintenance.
- Completed and Cancelled are final; Reported -> Completed is refused.
- Priority and details editable while open; every change audited on the asset (maintenance.status_changed /
  maintenance.updated) in the same transaction; a request's history = its audit rows.
- Retiring an asset with an open request is refused (S14).

Done-check (build plan): an asset under repair cannot be assigned, and its history shows each status change."""

import threading
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.audit import service as audit_service
from tests.test_asset_edit_retire import audit_rows, set_status, stored
from tests.test_assign_asset import (  # noqa: F401  (pytest fixtures used by name)
    ASSETS,
    assign,
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
from tests.test_report_problem import report, requests_of

REQUESTS = "/api/v1/maintenance-requests"


def start(client, headers, ref="MNT-000001", **body):
    return client.post(f"{REQUESTS}/{ref}/start", headers=headers, json=body)


def complete(client, headers, ref="MNT-000001", notes="Replaced the screen cable", **body):
    return client.post(f"{REQUESTS}/{ref}/complete", headers=headers, json={"repair_notes": notes, **body})


def cancel(client, headers, ref="MNT-000001", reason="Reported by mistake"):
    return client.post(f"{REQUESTS}/{ref}/cancel", headers=headers, json={"reason": reason})


def edit(client, headers, ref="MNT-000001", **body):
    return client.patch(f"{REQUESTS}/{ref}", headers=headers, json=body)


def days(n: int) -> str:
    return (today() + timedelta(days=n)).isoformat()


@pytest.fixture
def reported(client, laptops):
    """MNT-000001 Reported on AST-000002 (Available), reported 3 days ago; the asset was added 10 days ago."""
    created_days_ago("AST-000002", 10)
    response = report(client, laptops, "AST-000002", "Screen flickers", reported_date=days(-3))
    assert response.status_code == 201, response.text
    return laptops


@pytest.fixture
def in_progress(client, reported):
    response = start(client, reported, started_date=days(-2), service_provider="Dell Service Centre")
    assert response.status_code == 200, response.text
    return reported


# ---- Start work (Reported -> In Progress) -------------------------------------------------------------
def test_start_work_makes_the_asset_under_maintenance(client, manager, reported):
    user, _ = manager
    response = start(client, reported, started_date=days(-2), service_provider="  Dell Service Centre  ")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["started_date"] == days(-2)
    assert body["started_by"]["id"] == user.id
    assert body["started_at"] is not None
    assert body["service_provider"] == "Dell Service Centre"  # trimmed
    assert body["asset"]["status"] == "under_maintenance"
    assert stored("AST-000002").status == "under_maintenance"


def test_start_date_is_today_by_default(client, reported):
    assert start(client, reported).json()["started_date"] == today().isoformat()


@pytest.mark.parametrize("status", ["available", "damaged", "under_maintenance"])
def test_work_can_start_from_available_damaged_or_under_maintenance(client, reported, status):
    set_status("AST-000002", status)

    response = start(client, reported)

    assert response.status_code == 200, response.text
    assert stored("AST-000002").status == "under_maintenance"


def test_an_assigned_asset_must_be_returned_first(client, laptops, people):
    """S1."""
    assign(client, laptops, "AST-000001", people["asha"])
    report(client, laptops, "AST-000001")

    refused = start(client, laptops)
    assert refused.status_code == 409
    assert error_code(refused) == "asset_assigned"
    assert "Return it first" in refused.json()["error"]["message"]
    assert stored("AST-000001").status == "assigned"

    returned = client.post(f"{ASSETS}/AST-000001/return", headers=laptops, json={"inspection_outcome": "available"})
    assert returned.status_code == 200
    assert start(client, laptops).status_code == 200
    assert stored("AST-000001").status == "under_maintenance"


def test_a_retired_asset_cannot_start_work(client, reported):
    set_status("AST-000002", "retired")

    response = start(client, reported)

    assert error_code(response) == "asset_retired"
    assert requests_of("AST-000002")[0].status == "reported"


def test_start_date_rules(client, reported):
    future = start(client, reported, started_date=days(1))
    assert error_code(future) == "started_date_in_future"

    early = start(client, reported, started_date=days(-4))
    assert error_code(early) == "started_date_before_reported"
    assert early.json()["error"]["details"] == {"reported_date": days(-3)}

    assert start(client, reported, started_date=days(-3)).status_code == 200  # the reported day is allowed


def test_starting_twice_is_refused(client, in_progress):
    again = start(client, in_progress)

    assert again.status_code == 409
    assert error_code(again) == "invalid_status_change"
    assert again.json()["error"]["details"] == {"from": "in_progress", "to": "in_progress"}


# ---- BR-05: an asset under repair cannot be assigned (done-check) -----------------------------------------
def test_an_asset_under_repair_cannot_be_assigned_or_retired(client, in_progress, people):
    refused = assign(client, in_progress, "AST-000002", people["asha"])
    assert refused.status_code == 409
    assert error_code(refused) == "asset_under_maintenance"

    retire = client.post(f"{ASSETS}/AST-000002/retire", headers=in_progress, json={"reason": "Old"})
    assert retire.status_code == 409
    assert stored("AST-000002").status == "under_maintenance"


# ---- Complete (In Progress -> Completed) -------------------------------------------------------------------
def test_completing_records_the_repair_and_keeps_the_asset_under_maintenance(client, manager, in_progress):
    user, _ = manager
    response = complete(client, in_progress, notes="  Replaced the screen cable  ", completion_date=days(-1), cost="1200.5")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["repair_notes"] == "Replaced the screen cable"
    assert body["completion_date"] == days(-1)
    assert body["cost"] == "1200.50"
    assert body["service_provider"] == "Dell Service Centre"  # kept from start
    assert body["completed_by"]["id"] == user.id
    assert stored("AST-000002").status == "under_maintenance"  # until the 6.3 inspection (MNT-07)


def test_completion_defaults_to_today_and_cost_is_optional(client, in_progress):
    body = complete(client, in_progress).json()
    assert (body["completion_date"], body["cost"]) == (today().isoformat(), None)


def test_cost_zero_is_allowed(client, in_progress):
    assert complete(client, in_progress, cost="0").json()["cost"] == "0.00"


@pytest.mark.parametrize("cost", ["-1", "10.555", "12345678901", "abc"])
def test_bad_costs_are_refused(client, in_progress, cost):
    response = complete(client, in_progress, cost=cost)
    assert error_code(response) == "validation_error"
    assert requests_of("AST-000002")[0].status == "in_progress"


@pytest.mark.parametrize("notes", [None, "", "   ", "x" * 1001])
def test_repair_notes_are_required_up_to_1000(client, in_progress, notes):
    response = client.post(f"{REQUESTS}/MNT-000001/complete", headers=in_progress, json={"repair_notes": notes})
    assert response.status_code == 422
    assert error_code(response) == "invalid_repair_notes"


def test_completion_date_rules(client, in_progress):
    assert error_code(complete(client, in_progress, completion_date=days(1))) == "completion_date_in_future"
    early = complete(client, in_progress, completion_date=days(-3))
    assert error_code(early) == "completion_date_before_start"
    assert early.json()["error"]["details"] == {"started_date": days(-2)}
    assert complete(client, in_progress, completion_date=days(-2)).status_code == 200  # the start day is allowed


def test_reported_cannot_jump_to_completed(client, reported):
    """S3."""
    response = complete(client, reported)

    assert response.status_code == 409
    assert error_code(response) == "invalid_status_change"
    assert "Start work first" in response.json()["error"]["message"]
    assert stored("AST-000002").status == "available"


def test_service_provider_up_to_200(client, reported):
    assert error_code(start(client, reported, service_provider="x" * 201)) == "invalid_service_provider"
    assert start(client, reported, service_provider="x" * 200).status_code == 200


# ---- Cancel -------------------------------------------------------------------------------------------------
def test_cancelling_a_reported_request_leaves_the_asset_unchanged(client, manager, reported):
    user, _ = manager
    response = cancel(client, reported, reason="  Reported by mistake  ")

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["status"], body["cancel_reason"], body["cancelled_by"]["id"]) == ("cancelled", "Reported by mistake", user.id)
    assert stored("AST-000002").status == "available"


def test_cancelling_during_repair_keeps_the_asset_under_maintenance(client, in_progress):
    """S2: until the 6.3 inspection."""
    assert cancel(client, in_progress).status_code == 200
    assert stored("AST-000002").status == "under_maintenance"


@pytest.mark.parametrize("reason", [None, "", "  ", "x" * 501])
def test_a_cancel_reason_is_required_up_to_500(client, reported, reason):
    response = client.post(f"{REQUESTS}/MNT-000001/cancel", headers=reported, json={"reason": reason})
    assert error_code(response) == "invalid_cancel_reason"


# ---- Final states (S4) ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("close", ["complete", "cancel"])
def test_completed_and_cancelled_are_final(client, in_progress, close):
    closed = complete(client, in_progress) if close == "complete" else cancel(client, in_progress)
    assert closed.status_code == 200

    for response in (start(client, in_progress), complete(client, in_progress), cancel(client, in_progress)):
        assert response.status_code == 409
        assert error_code(response) == "invalid_status_change"
    assert error_code(edit(client, in_progress, priority="high")) == "maintenance_request_closed"


def test_after_closing_a_new_request_can_be_reported(client, in_progress):
    cancel(client, in_progress)
    # Slice 6.3 (revises O2): cancelled during repair, so it awaits inspection first.
    waiting = report(client, in_progress, "AST-000002", "Still flickers")
    assert (waiting.status_code, error_code(waiting)) == (409, "maintenance_request_awaiting_inspection")
    inspected = client.post(
        f"{REQUESTS}/MNT-000001/inspect", headers=in_progress, json={"inspection_outcome": "available"}
    )
    assert inspected.status_code == 200, inspected.text

    response = report(client, in_progress, "AST-000002", "Still flickers")

    assert response.status_code == 201
    assert response.json()["request_number"] == "MNT-000002"


# ---- Editing priority and details (S6, S9, S10, S12) ------------------------------------------------------------
def test_priority_and_details_can_be_edited_while_open(client, in_progress):
    response = edit(client, in_progress, priority="high", repair_notes="Waiting for part", cost="300")

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["priority"], body["repair_notes"], body["cost"]) == ("high", "Waiting for part", "300.00")
    [row] = audit_rows("AST-000002", "maintenance.updated")
    assert row.before_data == {"request_id": body["id"], "request_number": "MNT-000001", "priority": None, "repair_notes": None, "cost": None}
    assert row.after_data == {"request_id": body["id"], "request_number": "MNT-000001", "priority": "high", "repair_notes": "Waiting for part", "cost": "300.00"}


def test_priority_can_change_while_reported_and_be_cleared(client, reported):
    assert edit(client, reported, priority="low").json()["priority"] == "low"
    assert edit(client, reported, priority=None).json()["priority"] is None


def test_an_edit_that_changes_nothing_writes_nothing(client, in_progress):
    edit(client, in_progress, priority="medium")
    again = edit(client, in_progress, priority="medium", service_provider="Dell Service Centre")

    assert again.status_code == 200
    assert len(audit_rows("AST-000002", "maintenance.updated")) == 1


@pytest.mark.parametrize(
    "body",
    [{"priority": "urgent"}, {"status": "completed"}, {"cost": "-5"}, {"completion_date": "2026-01-01"}],
)
def test_bad_edits_are_a_validation_error(client, reported, body):
    assert error_code(edit(client, reported, **body)) == "validation_error"


# ---- History and audit (BR-13, MNT-06, U6; done-check) --------------------------------------------------------------
def test_history_shows_each_status_change(client, manager, in_progress):
    user, _ = manager
    complete(client, in_progress, cost="99.99")

    rows = audit_rows("AST-000002")
    actions = [r.action for r in rows]
    assert actions == ["asset.created", "maintenance.reported", "maintenance.status_changed", "maintenance.status_changed"]
    started, completed = rows[2], rows[3]
    request_id = requests_of("AST-000002")[0].id
    assert started.actor_user_id == user.id
    assert started.before_data == {"request_id": request_id, "request_number": "MNT-000001", "status": "reported", "asset_status": "available"}
    assert started.after_data == {
        "request_id": request_id, "request_number": "MNT-000001", "status": "in_progress",
        "asset_status": "under_maintenance", "started_date": days(-2), "service_provider": "Dell Service Centre",
    }
    assert completed.after_data["status"] == "completed"
    assert completed.after_data["cost"] == "99.99"
    assert completed.after_data["asset_status"] == "under_maintenance"

    detail = client.get(f"{REQUESTS}/MNT-000001", headers=in_progress).json()
    assert [h["action"] for h in detail["history"]] == [
        "maintenance.status_changed", "maintenance.status_changed", "maintenance.reported",
    ]
    asset_history = client.get(f"{ASSETS}/AST-000002/history", headers=in_progress).json()["items"]
    assert [e["action"] for e in asset_history][:3] == [
        "maintenance.status_changed", "maintenance.status_changed", "maintenance.reported",
    ]


def test_a_requests_history_leaves_out_other_requests(client, in_progress):
    cancel(client, in_progress)
    # Slice 6.3: cancelled during repair, so it is inspected before a new request can be reported.
    client.post(f"{REQUESTS}/MNT-000001/inspect", headers=in_progress, json={"inspection_outcome": "available"})
    report(client, in_progress, "AST-000002", "Another problem")

    second = client.get(f"{REQUESTS}/MNT-000002", headers=in_progress).json()
    assert [h["action"] for h in second["history"]] == ["maintenance.reported"]


@pytest.mark.parametrize("action", ["start", "complete", "cancel", "edit"])
def test_a_failing_audit_row_saves_nothing(client, reported, monkeypatch, action):
    if action == "complete":
        start(client, reported)
    before_status = stored("AST-000002").status
    before_request = requests_of("AST-000002")[0]

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(audit_service, "record", broken_record)
    with pytest.raises(RuntimeError):
        {"start": lambda: start(client, reported), "complete": lambda: complete(client, reported),
         "cancel": lambda: cancel(client, reported), "edit": lambda: edit(client, reported, priority="high")}[action]()

    after_request = requests_of("AST-000002")[0]
    assert (after_request.status, after_request.priority, after_request.updated_at) == (
        before_request.status, before_request.priority, before_request.updated_at,
    )
    assert stored("AST-000002").status == before_status


def test_the_database_keeps_progress_fields_consistent(reported):
    with SessionLocal() as s:
        with pytest.raises(IntegrityError):  # In Progress without a start
            s.execute(text("UPDATE maintenance_requests SET status = 'in_progress'"))
            s.commit()
    with SessionLocal() as s:
        with pytest.raises(IntegrityError):  # negative cost
            s.execute(text("UPDATE maintenance_requests SET cost = -1"))
            s.commit()


# ---- Retiring with an open request (S14) ----------------------------------------------------------------------------
def test_an_asset_with_an_open_request_cannot_be_retired(client, reported):
    response = client.post(f"{ASSETS}/AST-000002/retire", headers=reported, json={"reason": "End of life"})

    assert response.status_code == 409
    assert error_code(response) == "asset_has_open_request"
    assert response.json()["error"]["details"] == {"request_number": "MNT-000001"}
    assert "Cancel or finish MNT-000001 first" in response.json()["error"]["message"]

    cancel(client, reported)
    assert client.post(f"{ASSETS}/AST-000002/retire", headers=reported, json={"reason": "End of life"}).status_code == 200


# ---- Two actions at the same moment (U5) --------------------------------------------------------------------------------
def _act_in_own_session(action, user_id, results, barrier):
    from app.core.errors import AppError
    from app.modules.maintenance import service
    from app.modules.users.models import User

    with SessionLocal() as session:
        actor = session.get(User, user_id)
        request = service.get_request(session, "MNT-000001")
        barrier.wait()
        try:
            if action == "start":
                service.start_work(session, actor=actor, request=request)
            else:
                service.cancel_request(session, actor=actor, request=request, reason="Not needed")
            results.append(("ok", action))
        except AppError as error:
            results.append(("error", error.code))


@pytest.mark.parametrize("pair", [("start", "start"), ("cancel", "cancel")])
def test_two_actions_at_the_same_moment_only_one_wins(manager, reported, pair):
    user, _ = manager
    results: list = []
    barrier = threading.Barrier(2)
    threads = [threading.Thread(target=_act_in_own_session, args=(a, user.id, results, barrier)) for a in pair]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(kind for kind, _ in results) == ["error", "ok"]
    assert ("error", "invalid_status_change") in results
    assert len(audit_rows("AST-000002", "maintenance.status_changed")) == 1


# ---- Reading, roles ---------------------------------------------------------------------------------------------------
def test_one_request_by_id_or_number(client, reported):
    request_id = requests_of("AST-000002")[0].id
    assert client.get(f"{REQUESTS}/{request_id}", headers=reported).json()["request_number"] == "MNT-000001"
    assert client.get(f"{REQUESTS}/mnt-000001", headers=reported).status_code == 200
    missing = client.get(f"{REQUESTS}/MNT-999999", headers=reported)
    assert (missing.status_code, error_code(missing)) == (404, "maintenance_request_not_found")
    assert error_code(start(client, reported, "MNT-999999")) == "maintenance_request_not_found"


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_progress_a_request(client, staff_headers, reported, role):
    _, headers = staff_headers(role)
    assert start(client, headers).status_code == 200
    assert complete(client, headers).status_code == 200


def test_employee_role_and_no_login_are_refused(client, staff_headers, reported):
    _, employee = staff_headers("Employee")
    for headers, code in ((employee, 403), ({}, 401)):
        assert client.get(f"{REQUESTS}/MNT-000001", headers=headers).status_code == code
        assert start(client, headers).status_code == code
        assert complete(client, headers).status_code == code
        assert cancel(client, headers).status_code == code
        assert edit(client, headers, priority="high").status_code == code
    assert requests_of("AST-000002")[0].status == "reported"
