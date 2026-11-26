"""Completion inspection (Slice 6.3: MNT-07, workflow 7.4, BR-05, BR-13; owner's answers in decisions.md
section 35, decisions V1-V9 in section 36).

- Only a request that is Completed, or Cancelled after work started, awaits inspection.
- The outcome (Available, Damaged, Retired) becomes the asset's status. Retired fills the asset's
  retirement record and writes asset.retired too (revises A3: retiring from Under Maintenance, only here).
- Condition notes: up to 1,000; required for Damaged and Retired; for Retired at most 500 (the reason).
- Inspection date: today by default, earlier allowed, not before completion (or cancellation), not future.
- Once and final; Admin and IT Manager only; one transaction; two at once -> one wins.
- While a request awaits inspection, no new request can be reported (revises O2).

Done-check (build plan): a completed repair does not make the asset Available until it passes inspection."""

import threading
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.audit import service as audit_service
from tests.test_asset_edit_retire import audit_rows, stored
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
from tests.test_repair_progress import (  # noqa: F401  (pytest fixtures used by name)
    REQUESTS,
    cancel,
    complete,
    days,
    in_progress,
    report,
    reported,
    start,
)
from tests.test_report_problem import requests_of


def inspect(client, headers, ref="MNT-000001", outcome="available", **body):
    payload = {"inspection_outcome": outcome, **body} if outcome is not None else body
    return client.post(f"{REQUESTS}/{ref}/inspect", headers=headers, json=payload)


@pytest.fixture
def completed(client, in_progress):
    """MNT-000001 on AST-000002: started 2 days ago, completed yesterday; the asset is Under Maintenance."""
    response = complete(client, in_progress, completion_date=days(-1))
    assert response.status_code == 200, response.text
    return in_progress


# ---- The done-check ------------------------------------------------------------------------------------------
def test_a_completed_repair_is_not_available_until_inspected(client, completed, people):
    assert stored("AST-000002").status == "under_maintenance"
    body = client.get(f"{REQUESTS}/MNT-000001", headers=completed).json()
    assert body["awaiting_inspection"] is True
    refused = assign(client, completed, "AST-000002", people["asha"])
    assert (refused.status_code, error_code(refused)) == (409, "asset_under_maintenance")

    response = inspect(client, completed)

    assert response.status_code == 200, response.text
    assert stored("AST-000002").status == "available"
    assert assign(client, completed, "AST-000002", people["asha"]).status_code == 200


# ---- Outcomes -------------------------------------------------------------------------------------------------
def test_available_records_the_inspection(client, manager, completed):
    user, _ = manager
    response = inspect(client, completed, inspection_date=days(0), condition_notes="  Works fine  ")

    body = response.json()
    assert body["status"] == "completed"  # the request's status is unchanged
    assert body["awaiting_inspection"] is False
    assert body["inspection_outcome"] == "available"
    assert body["inspection_date"] == days(0)
    assert body["inspection_notes"] == "Works fine"
    assert body["inspected_by"]["email"] == user.email
    assert body["inspected_at"] is not None
    assert body["asset"]["status"] == "available"


def test_available_notes_are_optional_and_date_defaults_to_today(client, completed):
    body = inspect(client, completed).json()
    assert (body["inspection_notes"], body["inspection_date"]) == (None, days(0))


def test_damaged_keeps_the_asset_out_of_use(client, completed, people):
    response = inspect(client, completed, "MNT-000001", "damaged", condition_notes="Hinge still loose")

    assert response.status_code == 200, response.text
    assert stored("AST-000002").status == "damaged"
    assert error_code(assign(client, completed, "AST-000002", people["asha"])) == "asset_damaged"
    # A new request can be opened (O1 allows Damaged; nothing awaits inspection any more).
    assert report(client, completed, "AST-000002", "Hinge loose").status_code == 201


def test_retired_fills_the_retirement_record_and_writes_both_audit_rows(client, manager, completed):
    user, _ = manager
    response = inspect(client, completed, "MNT-000001", "retired", condition_notes="  Motherboard dead  ")

    assert response.status_code == 200, response.text
    asset = stored("AST-000002")
    assert asset.status == "retired"
    assert asset.retire_reason == "Motherboard dead"
    assert asset.retired_by_user_id == user.id
    assert asset.retired_at is not None
    retired = audit_rows("AST-000002", "asset.retired")
    assert len(retired) == 1
    assert retired[0].before_data == {"status": "under_maintenance"}
    assert retired[0].after_data["status"] == "retired"
    assert retired[0].after_data["reason"] == "Motherboard dead"
    assert retired[0].after_data["request_number"] == "MNT-000001"
    # Read-only afterwards, as any retired asset (A3 / F8).
    assert client.patch(f"{ASSETS}/AST-000002", headers=completed, json={"name": "X"}).status_code == 409


def test_the_retire_button_rule_is_unchanged_for_under_maintenance(client, completed):
    response = client.post(f"{ASSETS}/AST-000002/retire", headers=completed, json={"reason": "End of life"})
    assert (response.status_code, error_code(response)) == (409, "asset_not_retirable")


@pytest.mark.parametrize("outcome", [None, "", "under_maintenance", "assigned", "AVAILABLE"])
def test_the_outcome_must_be_one_of_three(client, completed, outcome):
    response = inspect(client, completed, outcome=outcome)
    assert (response.status_code, error_code(response)) == (422, "invalid_inspection_outcome")
    assert stored("AST-000002").status == "under_maintenance"


# ---- Notes and date ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("outcome", ["damaged", "retired"])
@pytest.mark.parametrize("notes", [None, "", "   "])
def test_notes_are_required_for_damaged_and_retired(client, completed, outcome, notes):
    response = inspect(client, completed, "MNT-000001", outcome, condition_notes=notes)
    assert (response.status_code, error_code(response)) == (422, "condition_notes_required")


def test_notes_up_to_1000(client, completed):
    too_long = inspect(client, completed, "MNT-000001", "damaged", condition_notes="x" * 1001)
    assert (too_long.status_code, error_code(too_long)) == (422, "invalid_condition_notes")
    assert inspect(client, completed, "MNT-000001", "damaged", condition_notes="x" * 1000).status_code == 200


def test_retired_notes_are_the_reason_so_at_most_500(client, completed):
    too_long = inspect(client, completed, "MNT-000001", "retired", condition_notes="x" * 501)
    assert (too_long.status_code, error_code(too_long)) == (422, "invalid_retire_reason")
    assert inspect(client, completed, "MNT-000001", "retired", condition_notes="x" * 500).status_code == 200


def test_inspection_date_rules(client, completed):
    future = inspect(client, completed, inspection_date=days(1))
    assert (future.status_code, error_code(future)) == (422, "inspection_date_in_future")
    early = inspect(client, completed, inspection_date=days(-2))
    assert (early.status_code, error_code(early)) == (422, "inspection_date_before_completion")
    assert early.json()["error"]["details"] == {"earliest_date": days(-1)}
    same_day = inspect(client, completed, inspection_date=days(-1))  # the completion day itself is allowed
    assert same_day.status_code == 200
    assert same_day.json()["inspection_date"] == days(-1)


# ---- Which requests can be inspected -------------------------------------------------------------------------------
def test_a_request_cancelled_during_repair_can_be_inspected(client, in_progress):
    assert cancel(client, in_progress).status_code == 200
    assert stored("AST-000002").status == "under_maintenance"

    early = inspect(client, in_progress, inspection_date=days(-1))  # before the day it was cancelled
    assert error_code(early) == "inspection_date_before_completion"
    response = inspect(client, in_progress)

    assert response.status_code == 200, response.text
    assert stored("AST-000002").status == "available"


def test_requests_not_awaiting_inspection_are_refused(client, reported):
    # Reported
    assert error_code(inspect(client, reported)) == "request_not_awaiting_inspection"
    # In Progress
    start(client, reported)
    assert error_code(inspect(client, reported)) == "request_not_awaiting_inspection"


def test_a_request_cancelled_before_work_started_needs_no_inspection(client, reported):
    cancel(client, reported)
    response = inspect(client, reported)
    assert (response.status_code, error_code(response)) == (409, "request_not_awaiting_inspection")
    assert "cancelled before work started" in response.json()["error"]["message"]


def test_an_inspection_is_final(client, completed):
    assert inspect(client, completed).status_code == 200
    again = inspect(client, completed, "MNT-000001", "damaged", condition_notes="Changed my mind")
    assert (again.status_code, error_code(again)) == (409, "request_not_awaiting_inspection")
    assert stored("AST-000002").status == "available"
    assert len(audit_rows("AST-000002", "maintenance.inspected")) == 1


def test_the_asset_must_still_be_under_maintenance(client, completed):
    with SessionLocal() as s:  # cannot happen through the app; the check is a safety net
        s.execute(text("UPDATE assets SET status = 'damaged' WHERE asset_code = 'AST-000002'"))
        s.commit()
    response = inspect(client, completed)
    assert (response.status_code, error_code(response)) == (409, "asset_not_under_maintenance")


def test_unknown_fields_are_refused(client, completed):
    response = inspect(client, completed, status="available")
    assert (response.status_code, error_code(response)) == (422, "validation_error")


# ---- Awaiting inspection blocks a new request (revises O2) -----------------------------------------------------
def test_no_new_request_while_one_awaits_inspection(client, completed):
    response = report(client, completed, "AST-000002", "Another problem")
    assert (response.status_code, error_code(response)) == (409, "maintenance_request_awaiting_inspection")
    assert response.json()["error"]["details"] == {"request_number": "MNT-000001"}

    inspect(client, completed)
    assert report(client, completed, "AST-000002", "Another problem").status_code == 201


def test_the_database_allows_one_blocking_request_per_asset(completed):
    with SessionLocal() as s:
        asset_id = s.execute(text("SELECT id FROM assets WHERE asset_code = 'AST-000002'")).scalar_one()
        user_id = s.execute(text("SELECT reported_by_user_id FROM maintenance_requests")).scalar_one()
        with pytest.raises(IntegrityError):
            s.execute(
                text(
                    "INSERT INTO maintenance_requests (asset_id, issue_description, reported_date, reported_by_user_id)"
                    " VALUES (:a, 'x', CURRENT_DATE, :u)"
                ),
                {"a": asset_id, "u": user_id},
            )
            s.commit()


def test_the_database_keeps_inspection_fields_consistent(reported):
    with SessionLocal() as s:  # a Reported request cannot carry an inspection
        with pytest.raises(IntegrityError):
            s.execute(
                text(
                    "UPDATE maintenance_requests SET inspection_outcome = 'available', inspection_date = CURRENT_DATE,"
                    " inspected_at = now(), inspected_by_user_id = reported_by_user_id"
                )
            )
            s.commit()


# ---- Lists, history, audit ---------------------------------------------------------------------------------------
def test_the_list_can_show_only_requests_awaiting_inspection(client, completed):
    report(client, completed, "AST-000001", "Keyboard sticky")
    waiting = client.get(REQUESTS, headers=completed, params={"status": "awaiting_inspection"}).json()
    assert [r["request_number"] for r in waiting["items"]] == ["MNT-000001"]

    inspect(client, completed)
    assert client.get(REQUESTS, headers=completed, params={"status": "awaiting_inspection"}).json()["total"] == 0


def test_history_shows_the_inspection(client, manager, completed):
    inspect(client, completed, "MNT-000001", "damaged", condition_notes="Hinge still loose", inspection_date=days(0))

    rows = audit_rows("AST-000002", "maintenance.inspected")
    assert len(rows) == 1
    assert rows[0].before_data == {
        "request_id": requests_of("AST-000002")[0].id, "request_number": "MNT-000001",
        "status": "completed", "asset_status": "under_maintenance",
    }
    assert rows[0].after_data["inspection_outcome"] == "damaged"
    assert rows[0].after_data["asset_status"] == "damaged"
    assert rows[0].after_data["inspection_date"] == days(0)
    assert rows[0].after_data["condition_notes"] == "Hinge still loose"
    history = client.get(f"{REQUESTS}/MNT-000001", headers=completed).json()["history"]
    assert history[0]["action"] == "maintenance.inspected"
    assert history[0]["actor"]["email"] == manager[0].email


@pytest.mark.parametrize("outcome", ["available", "retired"])
def test_a_failing_audit_row_saves_nothing(client, completed, monkeypatch, outcome):
    def broken_record(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(audit_service, "record", broken_record)
    with pytest.raises(RuntimeError):
        inspect(client, completed, "MNT-000001", outcome, condition_notes="Dead")

    asset = stored("AST-000002")
    assert (asset.status, asset.retire_reason) == ("under_maintenance", None)
    assert requests_of("AST-000002")[0].inspected_at is None


def _inspect_in_own_session(user_id, outcome, results, barrier):
    from app.core.errors import AppError
    from app.modules.maintenance import service
    from app.modules.users.models import User

    with SessionLocal() as session:
        actor = session.get(User, user_id)
        request = service.get_request(session, "MNT-000001")
        barrier.wait()
        try:
            service.inspect_request(
                session, actor=actor, request=request, inspection_outcome=outcome, condition_notes="Checked"
            )
            results.append(("ok", outcome))
        except AppError as error:
            results.append(("error", error.code))


def test_two_inspections_at_the_same_moment_only_one_wins(manager, completed):
    user, _ = manager
    results: list = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_inspect_in_own_session, args=(user.id, o, results, barrier))
        for o in ("available", "damaged")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(kind for kind, _ in results) == ["error", "ok"]
    assert ("error", "request_not_awaiting_inspection") in results
    assert len(audit_rows("AST-000002", "maintenance.inspected")) == 1


# ---- Roles --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_inspect(client, staff_headers, completed, role):
    _, headers = staff_headers(role)
    assert inspect(client, headers).status_code == 200


def test_employee_role_and_no_login_are_refused(client, staff_headers, completed):
    _, employee = staff_headers("Employee")
    assert inspect(client, employee).status_code == 403
    assert inspect(client, {}).status_code == 401
    assert stored("AST-000002").status == "under_maintenance"
