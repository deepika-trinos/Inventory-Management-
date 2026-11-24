"""Return and inspection (Slice 5.2: ASN-05, ASN-06, BR-04, BR-13; owner's answers Q5, N4, N5,
N9; decisions in decisions.md section 28).

- POST /assets/{ref}/return: only for an assigned asset; return date today by default, earlier
  allowed, not before the assignment date, never in the future; inspection outcome required
  (Available / Under Maintenance / Damaged); condition notes up to 1,000, required unless
  the outcome is Available.
- Closes the open assignment (kept with its return details, ASN-07) and sets the asset's
  status from the outcome; Under Maintenance sets the status only (N5).
- One transaction with audit assignment.returned; a failure saves nothing; two returns at
  the same moment: only one succeeds.

Done-check (build plan): a good return becomes Available and a damaged one does not."""

import threading
from datetime import timedelta

import pytest

from app.core.database import SessionLocal
from app.modules.audit import service as audit_service
from tests.test_asset_edit_retire import audit_rows, stored
from tests.test_assign_asset import (  # noqa: F401  (pytest fixtures used by name)
    ASSETS,
    EMPLOYEES,
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


def give_back(client, headers, code, outcome="available", **body):
    payload = {"inspection_outcome": outcome, **body}
    return client.post(f"{ASSETS}/{code}/return", headers=headers, json=payload)


@pytest.fixture
def assigned(client, laptops, people):
    """AST-000001 assigned to Asha Kumar (EMP-001) five days ago (asset added ten days ago)."""
    created_days_ago("AST-000001", 10)
    response = assign(client, laptops, "AST-000001", people["asha"], assignment_date=(today() - timedelta(days=5)).isoformat())
    assert response.status_code == 200, response.text
    return laptops


# ---- Each outcome ------------------------------------------------------------------------------------
def test_a_good_return_becomes_available_and_keeps_the_assignment(client, manager, assigned, people):
    user, _ = manager
    response = give_back(client, assigned, "AST-000001", "available")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "available"
    assert body["current_assignment"] is None
    [row] = assignments("AST-000001")  # kept, not deleted or overwritten (ASN-07)
    assert row.employee_id == people["asha"]
    assert row.assignment_date == today() - timedelta(days=5)
    assert (row.return_date, row.return_outcome, row.condition_notes, row.returned_by_user_id) == (
        today(), "available", None, user.id,
    )
    assert row.returned_at is not None


@pytest.mark.parametrize("outcome", ["damaged", "under_maintenance"])
def test_a_damaged_or_maintenance_return_does_not_become_available(client, assigned, outcome):
    response = give_back(client, assigned, "AST-000001", outcome, condition_notes="  Screen cracked  ")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == outcome
    [row] = assignments("AST-000001")
    assert (row.return_outcome, row.condition_notes) == (outcome, "Screen cracked")  # trimmed


def test_notes_are_optional_but_kept_for_an_available_return(client, assigned):
    give_back(client, assigned, "AST-000001", "available", condition_notes="Minor scratches, works fine")
    [row] = assignments("AST-000001")
    assert row.condition_notes == "Minor scratches, works fine"


def test_under_maintenance_sets_the_status_only(client, assigned):
    """N5: no maintenance request is created (Phase 6); only the asset's status changes."""
    give_back(client, assigned, "AST-000001", "under_maintenance", condition_notes="Keyboard not working")

    assert stored("AST-000001").status == "under_maintenance"
    actions = [r.action for r in audit_rows("AST-000001")]
    assert actions == ["asset.created", "assignment.created", "assignment.returned"]


# ---- Notes and outcome (N4) ----------------------------------------------------------------------------
@pytest.mark.parametrize("outcome", ["damaged", "under_maintenance"])
@pytest.mark.parametrize("notes", [None, "", "    "])
def test_notes_are_required_for_damaged_or_maintenance(client, assigned, outcome, notes):
    response = give_back(client, assigned, "AST-000001", outcome, condition_notes=notes)

    assert response.status_code == 422
    assert error_code(response) == "condition_notes_required"
    assert stored("AST-000001").status == "assigned"
    assert assignments("AST-000001")[0].returned_at is None


def test_notes_up_to_1000_characters(client, assigned):
    too_long = give_back(client, assigned, "AST-000001", "damaged", condition_notes="x" * 1001)
    assert too_long.status_code == 422
    assert error_code(too_long) == "invalid_condition_notes"

    exact = give_back(client, assigned, "AST-000001", "damaged", condition_notes="x" * 1000)
    assert exact.status_code == 200


@pytest.mark.parametrize("outcome", [None, "", "retired", "assigned", "Available"])
def test_the_outcome_is_required_and_must_be_one_of_three(client, assigned, outcome):
    response = client.post(f"{ASSETS}/AST-000001/return", headers=assigned, json={"inspection_outcome": outcome, "condition_notes": "x"})

    assert response.status_code == 422
    assert error_code(response) == "invalid_inspection_outcome"
    assert stored("AST-000001").status == "assigned"


# ---- Dates (N4) ------------------------------------------------------------------------------------------
def test_an_earlier_return_date_is_allowed(client, assigned):
    on = today() - timedelta(days=2)
    response = give_back(client, assigned, "AST-000001", return_date=on.isoformat())

    assert response.status_code == 200
    assert assignments("AST-000001")[0].return_date == on


def test_a_return_on_the_assignment_date_is_allowed(client, assigned):
    response = give_back(client, assigned, "AST-000001", return_date=(today() - timedelta(days=5)).isoformat())
    assert response.status_code == 200


def test_a_return_date_before_the_assignment_date_is_refused(client, assigned):
    response = give_back(client, assigned, "AST-000001", return_date=(today() - timedelta(days=6)).isoformat())

    assert response.status_code == 422
    assert error_code(response) == "return_date_before_assignment"
    assert response.json()["error"]["details"] == {"assignment_date": (today() - timedelta(days=5)).isoformat()}
    assert stored("AST-000001").status == "assigned"


def test_a_future_return_date_is_refused(client, assigned):
    response = give_back(client, assigned, "AST-000001", return_date=(today() + timedelta(days=1)).isoformat())

    assert response.status_code == 422
    assert error_code(response) == "return_date_in_future"
    assert assignments("AST-000001")[0].returned_at is None


@pytest.mark.parametrize(
    "body",
    [
        {"inspection_outcome": "available", "return_date": "not-a-date"},
        {"inspection_outcome": "available", "status": "available"},  # unknown field
        {"inspection_outcome": "available", "returned_by_user_id": 1},
    ],
)
def test_bad_bodies_are_a_validation_error(client, assigned, body):
    response = client.post(f"{ASSETS}/AST-000001/return", headers=assigned, json=body)

    assert response.status_code == 422
    assert error_code(response) == "validation_error"


# ---- Not assigned ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("status", ["available", "under_maintenance", "damaged", "retired"])
def test_an_asset_that_is_not_assigned_cannot_be_returned(client, laptops, people, status):
    from tests.test_asset_edit_retire import set_status

    set_status("AST-000002", status)
    response = give_back(client, laptops, "AST-000002")

    assert response.status_code == 409
    assert error_code(response) == "asset_not_assigned"
    assert response.json()["error"]["details"] == {"status": status}
    assert stored("AST-000002").status == status


def test_an_asset_cannot_be_returned_twice(client, assigned):
    assert give_back(client, assigned, "AST-000001").status_code == 200

    again = give_back(client, assigned, "AST-000001")

    assert error_code(again) == "asset_not_assigned"
    assert len(audit_rows("AST-000001", "assignment.returned")) == 1


# ---- Assigning again after a return ---------------------------------------------------------------------------
def test_after_an_available_return_the_asset_can_be_assigned_again(client, assigned, people):
    give_back(client, assigned, "AST-000001", "available")

    response = assign(client, assigned, "AST-000001", people["ravi"])

    assert response.status_code == 200
    assert response.json()["current_assignment"]["employee"]["employee_code"] == "EMP-002"
    rows = assignments("AST-000001")
    assert [(r.employee_id, r.returned_at is None) for r in rows] == [(people["asha"], False), (people["ravi"], True)]


@pytest.mark.parametrize("outcome, code", [("damaged", "asset_damaged"), ("under_maintenance", "asset_under_maintenance")])
def test_after_a_damaged_or_maintenance_return_it_cannot_be_assigned(client, assigned, people, outcome, code):
    give_back(client, assigned, "AST-000001", outcome, condition_notes="Screen cracked")

    response = assign(client, assigned, "AST-000001", people["ravi"])

    assert response.status_code == 409
    assert error_code(response) == code
    assert len(assignments("AST-000001")) == 1


def test_after_returning_everything_the_employee_can_be_deactivated(client, assigned, people):
    """N6 lifts once the employee holds nothing."""
    blocked = client.post(f"{EMPLOYEES}/{people['asha']}/deactivate", headers=assigned)
    assert error_code(blocked) == "employee_has_assets"

    give_back(client, assigned, "AST-000001")

    allowed = client.post(f"{EMPLOYEES}/{people['asha']}/deactivate", headers=assigned)
    assert allowed.status_code == 200


def test_an_inactive_holder_can_still_return_the_asset(client, assigned, people, db):
    """An employee made inactive while holding an asset (e.g. by hand, before N6) can still return it."""
    from sqlalchemy import text

    db.execute(text("UPDATE employees SET status = 'inactive' WHERE id = :i"), {"i": people["asha"]})
    db.commit()

    assert give_back(client, assigned, "AST-000001").status_code == 200


def test_the_register_no_longer_shows_a_holder_after_return(client, assigned, people):
    give_back(client, assigned, "AST-000001")

    rows = {r["asset_code"]: r for r in client.get(ASSETS, headers=assigned).json()["items"]}
    assert rows["AST-000001"]["assigned_to"] is None
    assert client.get(ASSETS, headers=assigned, params={"assigned_to": people["asha"]}).json()["total"] == 0


# ---- Audit (BR-13) -------------------------------------------------------------------------------------------------
def test_the_return_writes_one_audit_row_with_the_details(client, manager, assigned, people):
    user, _ = manager
    give_back(client, assigned, "AST-000001", "damaged", condition_notes="Screen cracked")

    [row] = audit_rows("AST-000001", "assignment.returned")
    [assignment] = assignments("AST-000001")
    assert row.actor_user_id == user.id
    assert row.before_data == {"status": "assigned"}
    assert row.after_data == {
        "status": "damaged", "assignment_id": assignment.id, "employee_id": people["asha"],
        "employee_code": "EMP-001", "employee_name": "Asha Kumar",
        "assignment_date": (today() - timedelta(days=5)).isoformat(), "return_date": today().isoformat(),
        "inspection_outcome": "damaged", "condition_notes": "Screen cracked",
    }
    history = client.get(f"{ASSETS}/AST-000001/history", headers=assigned).json()["items"]
    assert [e["action"] for e in history][:2] == ["assignment.returned", "assignment.created"]


def test_a_failing_audit_row_saves_nothing(client, assigned, monkeypatch):
    def broken_record(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(audit_service, "record", broken_record)
    with pytest.raises(RuntimeError):
        give_back(client, assigned, "AST-000001", "damaged", condition_notes="Screen cracked")

    assert stored("AST-000001").status == "assigned"
    [row] = assignments("AST-000001")
    assert (row.returned_at, row.return_date, row.return_outcome, row.condition_notes) == (None, None, None, None)
    assert audit_rows("AST-000001", "assignment.returned") == []


# ---- Two returns at the same moment -------------------------------------------------------------------------------
def _return_in_own_session(asset_code, user_id, outcome, results, barrier):
    from app.core.errors import AppError
    from app.modules.assets import service as assets_service
    from app.modules.assignments import service
    from app.modules.users.models import User

    with SessionLocal() as session:
        actor = session.get(User, user_id)
        asset = assets_service.get_asset(session, asset_code)
        barrier.wait()
        try:
            service.return_asset(session, actor=actor, asset=asset, inspection_outcome=outcome, condition_notes="Checked")
            results.append(("ok", outcome))
        except AppError as error:
            results.append(("error", error.code))


def test_two_returns_at_the_same_moment_only_one_wins(manager, assigned):
    user, _ = manager
    results: list = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_return_in_own_session, args=("AST-000001", user.id, outcome, results, barrier))
        for outcome in ("available", "damaged")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(kind for kind, _ in results) == ["error", "ok"]
    assert ("error", "asset_not_assigned") in results
    winner = next(value for kind, value in results if kind == "ok")
    assert stored("AST-000001").status == winner
    [row] = assignments("AST-000001")
    assert row.return_outcome == winner
    assert len(audit_rows("AST-000001", "assignment.returned")) == 1


# ---- Roles ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_return(client, staff_headers, assigned, role):
    _, headers = staff_headers(role)
    assert give_back(client, headers, "AST-000001").status_code == 200


def test_employee_role_cannot_return(client, staff_headers, assigned):
    _, headers = staff_headers("Employee")

    response = give_back(client, headers, "AST-000001")

    assert response.status_code == 403
    assert error_code(response) == "forbidden"
    assert stored("AST-000001").status == "assigned"


def test_return_needs_login(client, assigned):
    assert client.post(f"{ASSETS}/AST-000001/return", json={"inspection_outcome": "available"}).status_code == 401


@pytest.mark.parametrize("ref", ["AST-999999", "99999"])
def test_unknown_asset_gives_404(client, assigned, ref):
    assert error_code(give_back(client, assigned, ref)) == "asset_not_found"
