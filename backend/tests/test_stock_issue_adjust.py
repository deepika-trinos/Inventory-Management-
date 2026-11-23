"""Stock issue and adjustment (Slice 4.4: INV-04, INV-07, BR-09, BR-10, BR-13, workflow 7.5;
owner's answers Q7, A4, A5, A4-5a/b/c; decisions in decisions.md section 23).

- POST /stock-items/{id}/issue: quantity, required reason, optional active employee,
  optional date (today by default, earlier allowed, never in the future).
- POST /stock-items/{id}/adjust: add or remove N with a required reason.
- Never below 0 (insufficient_stock); exactly 0 allowed; inactive items refused.
- Balance, movement and audit row are saved in one transaction; a failure saves nothing.

Done-check (build plan): issuing more than is in stock is blocked, and every change
appears in history with its user and reason."""

import threading
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditLog
from app.modules.employees import service as employees_service
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import MovementType, StockItem, StockMovement
from tests.test_purchases_api import (  # noqa: F401  (pytest fixtures used by name)
    data,
    error_code,
    manager,
    staff_headers,
)

ITEMS = "/api/v1/stock-items"
START = 25  # the USB mouse's balance in the purchases `data` fixture


def issue(client, headers, item_id, **body):
    body = {"quantity": 1, "reason": "New joiner kit", **body}
    return client.post(f"{ITEMS}/{item_id}/issue", headers=headers, json=body)


def adjust(client, headers, item_id, **body):
    body = {"direction": "remove", "quantity": 1, "reason": "Broken", **body}
    return client.post(f"{ITEMS}/{item_id}/adjust", headers=headers, json=body)


def on_hand(item_id: int) -> int:
    with SessionLocal() as s:
        return s.get(StockItem, item_id).quantity_on_hand


def movements(item_id: int) -> list[StockMovement]:
    with SessionLocal() as s:
        return list(s.scalars(select(StockMovement).where(StockMovement.stock_item_id == item_id).order_by(StockMovement.id)))


def audit_rows(item_id: int, action: str | None = None) -> list[AuditLog]:
    """The item's stock-change audit rows (stock.issued / stock.adjusted), not its own
    stock_item.created / updated rows."""
    actions = [action] if action else ["stock.issued", "stock.adjusted"]
    with SessionLocal() as s:
        stmt = select(AuditLog).where(
            AuditLog.entity_type == "stock_items", AuditLog.entity_id == str(item_id), AuditLog.action.in_(actions)
        )
        return list(s.scalars(stmt.order_by(AuditLog.id)))


@pytest.fixture
def people(db):
    """Asha Kumar (active) and Ravi Shah (inactive)."""
    asha = employees_service.create_employee(db, data={"employee_code": "EMP-001", "full_name": "Asha Kumar"})
    ravi = employees_service.create_employee(db, data={"employee_code": "EMP-002", "full_name": "Ravi Shah"})
    employees_service.set_active(db, actor=None, employee=ravi, active=False)
    return {"asha": asha.id, "ravi": ravi.id}


# ---- Done-check ---------------------------------------------------------------------------------
def test_issuing_more_than_in_stock_is_blocked_and_saves_nothing(client, manager, data):
    _, headers = manager

    response = issue(client, headers, data["mouse"], quantity=START + 1)

    assert response.status_code == 409
    body = response.json()["error"]
    assert body["code"] == "insufficient_stock"
    assert body["details"] == {"stock_item_id": data["mouse"], "quantity_on_hand": START, "requested": START + 1}
    assert on_hand(data["mouse"]) == START
    assert movements(data["mouse"]) == [] and audit_rows(data["mouse"]) == []


def test_every_change_appears_in_history_with_its_user_and_reason(client, manager, data, people):
    user, headers = manager
    issue(client, headers, data["mouse"], quantity=3, reason="Training room 2", employee_id=None)
    issue(client, headers, data["mouse"], quantity=1, reason="Replacement mouse", employee_id=people["asha"])
    adjust(client, headers, data["mouse"], direction="add", quantity=2, reason="Found two in the store room")
    adjust(client, headers, data["mouse"], direction="remove", quantity=4, reason="Four broken, scrapped")

    rows = client.get(f"{ITEMS}/{data['mouse']}/movements", headers=headers).json()["items"]

    assert [(r["movement_type"], r["change"], r["balance_after"], r["reason"]) for r in rows] == [
        ("adjustment_out", -4, 19, "Four broken, scrapped"),
        ("adjustment_in", 2, 23, "Found two in the store room"),
        ("issue", -1, 21, "Replacement mouse"),
        ("issue", -3, 22, "Training room 2"),
    ]
    assert all(r["created_by"] == {"id": user.id, "email": user.email} for r in rows)
    assert rows[2]["issued_to"] == {"id": people["asha"], "employee_code": "EMP-001", "full_name": "Asha Kumar"}
    assert rows[3]["issued_to"] is None


# ---- Issue --------------------------------------------------------------------------------------
def test_issue_lowers_the_balance_and_returns_item_and_movement(client, manager, data, people):
    _, headers = manager

    response = issue(client, headers, data["mouse"], quantity=5, reason="  New joiner kits  ", employee_id=people["asha"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["item"]["quantity_on_hand"] == START - 5
    m = body["movement"]
    assert (m["movement_type"], m["direction"], m["quantity"], m["change"], m["balance_after"]) == ("issue", "out", 5, -5, 20)
    assert m["reason"] == "New joiner kits"  # trimmed
    assert m["movement_date"] == inventory_service._today().isoformat()  # today by default
    assert m["issued_to"]["employee_code"] == "EMP-001"
    assert on_hand(data["mouse"]) == 20


def test_issuing_exactly_everything_takes_stock_to_zero(client, manager, data):
    _, headers = manager
    response = issue(client, headers, data["mouse"], quantity=START, reason="Moved to branch office")
    assert response.status_code == 200
    assert on_hand(data["mouse"]) == 0
    assert response.json()["item"]["low_stock"] is True  # 0 <= threshold 5 (B37)


def test_issue_to_an_inactive_employee_is_refused(client, manager, data, people):
    _, headers = manager
    response = issue(client, headers, data["mouse"], employee_id=people["ravi"])
    assert response.status_code == 409 and error_code(response) == "employee_inactive"
    assert on_hand(data["mouse"]) == START


def test_issue_to_an_unknown_employee_is_404(client, manager, data):
    _, headers = manager
    response = issue(client, headers, data["mouse"], employee_id=99999)
    assert response.status_code == 404 and error_code(response) == "employee_not_found"
    assert on_hand(data["mouse"]) == START


def test_an_earlier_date_is_allowed_and_a_future_date_refused(client, manager, data):
    _, headers = manager
    yesterday = inventory_service._today() - timedelta(days=1)
    tomorrow = inventory_service._today() + timedelta(days=1)

    earlier = issue(client, headers, data["mouse"], movement_date=yesterday.isoformat())
    future = issue(client, headers, data["mouse"], movement_date=tomorrow.isoformat())

    assert earlier.status_code == 200 and earlier.json()["movement"]["movement_date"] == yesterday.isoformat()
    assert future.status_code == 422 and error_code(future) == "movement_date_in_future"
    assert on_hand(data["mouse"]) == START - 1


# ---- Adjust -------------------------------------------------------------------------------------
def test_adjust_add_and_remove(client, manager, data):
    _, headers = manager

    added = adjust(client, headers, data["mouse"], direction="add", quantity=10, reason="Count found 10 more")
    removed = adjust(client, headers, data["mouse"], direction="remove", quantity=35, reason="Store flooded")

    assert added.status_code == 200 and added.json()["movement"]["movement_type"] == "adjustment_in"
    assert added.json()["item"]["quantity_on_hand"] == 35
    assert removed.status_code == 200 and removed.json()["movement"]["movement_type"] == "adjustment_out"
    assert on_hand(data["mouse"]) == 0  # exactly 0 is allowed


def test_removing_more_than_on_hand_is_refused(client, manager, data):
    _, headers = manager
    response = adjust(client, headers, data["mouse"], direction="remove", quantity=START + 1)
    assert response.status_code == 409 and error_code(response) == "insufficient_stock"
    assert on_hand(data["mouse"]) == START


def test_an_adjustment_cannot_name_an_employee(client, manager, data, people):
    _, headers = manager
    response = adjust(client, headers, data["mouse"], employee_id=people["asha"])
    assert response.status_code == 422 and error_code(response) == "validation_error"


@pytest.mark.parametrize("direction", ["", "set", "ADD", None])
def test_direction_must_be_add_or_remove(client, manager, data, direction):
    _, headers = manager
    response = adjust(client, headers, data["mouse"], direction=direction)
    assert response.status_code == 422 and error_code(response) == "validation_error"


# ---- Shared rules for both ------------------------------------------------------------------------
@pytest.mark.parametrize("action", [issue, adjust])
@pytest.mark.parametrize("reason", [None, "", "    "])
def test_a_reason_is_required(client, manager, data, action, reason):
    _, headers = manager
    response = action(client, headers, data["mouse"], reason=reason)
    assert response.status_code == 422 and error_code(response) == "invalid_reason"
    assert on_hand(data["mouse"]) == START and movements(data["mouse"]) == []


@pytest.mark.parametrize("action", [issue, adjust])
def test_reason_up_to_500_characters(client, manager, data, action):
    _, headers = manager
    too_long = action(client, headers, data["mouse"], reason="r" * 501)
    exactly = action(client, headers, data["mouse"], reason="r" * 500)
    assert too_long.status_code == 422 and error_code(too_long) == "invalid_reason"
    assert exactly.status_code == 200


@pytest.mark.parametrize("action", [issue, adjust])
@pytest.mark.parametrize("quantity", [0, -1, 1.5, "two", None, 1_000_001])
def test_quantity_is_a_whole_number_above_zero(client, manager, data, action, quantity):
    _, headers = manager
    response = action(client, headers, data["mouse"], quantity=quantity)
    assert response.status_code == 422 and error_code(response) == "validation_error"
    assert on_hand(data["mouse"]) == START


@pytest.mark.parametrize("action", [issue, adjust])
def test_an_inactive_item_is_refused(client, manager, data, action):
    _, headers = manager
    response = action(client, headers, data["old_mouse"], direction="add") if action is adjust else action(client, headers, data["old_mouse"])
    assert response.status_code == 409 and error_code(response) == "stock_item_inactive"
    assert movements(data["old_mouse"]) == []


@pytest.mark.parametrize("action", [issue, adjust])
def test_unknown_item_is_404(client, manager, data, action):
    _, headers = manager
    response = action(client, headers, 99999)
    assert response.status_code == 404 and error_code(response) == "stock_item_not_found"


@pytest.mark.parametrize("action", [issue, adjust])
def test_unknown_fields_are_refused(client, manager, data, action):
    _, headers = manager
    response = action(client, headers, data["mouse"], balance_after=1)
    assert response.status_code == 422 and error_code(response) == "validation_error"


# ---- Audit and consistency (BR-13, B39) ----------------------------------------------------------------
def test_issue_and_adjustment_each_write_one_audit_row(client, manager, data, people):
    user, headers = manager
    issued = issue(client, headers, data["mouse"], quantity=2, reason="Kits", employee_id=people["asha"]).json()
    adjusted = adjust(client, headers, data["mouse"], direction="remove", quantity=1, reason="Broken").json()

    [issue_row] = audit_rows(data["mouse"], "stock.issued")
    [adjust_row] = audit_rows(data["mouse"], "stock.adjusted")
    assert issue_row.actor_user_id == user.id and adjust_row.actor_user_id == user.id
    assert issue_row.before_data == {"quantity_on_hand": 25}
    assert issue_row.after_data["quantity_on_hand"] == 23
    assert issue_row.after_data["movement_id"] == issued["movement"]["id"]
    assert issue_row.after_data["reason"] == "Kits"
    assert issue_row.after_data["issued_to"] == {"id": people["asha"], "employee_code": "EMP-001", "full_name": "Asha Kumar"}
    assert adjust_row.after_data["movement_type"] == "adjustment_out"
    assert adjust_row.after_data["movement_id"] == adjusted["movement"]["id"]
    assert "issued_to" not in adjust_row.after_data


def test_balance_always_equals_the_last_balance_after(client, manager, data):
    _, headers = manager
    for action, body in [
        (issue, {"quantity": 4}), (adjust, {"direction": "add", "quantity": 7}),
        (issue, {"quantity": 9}), (adjust, {"direction": "remove", "quantity": 3}),
    ]:
        assert action(client, headers, data["mouse"], **body).status_code == 200
        assert movements(data["mouse"])[-1].balance_after == on_hand(data["mouse"])
    assert on_hand(data["mouse"]) == START - 4 + 7 - 9 - 3


@pytest.mark.parametrize("action", ["issue", "adjust"])
def test_a_forced_error_saves_nothing(client, manager, data, monkeypatch, action):
    _, headers = manager

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(audit_service, "record", broken_record)
    with pytest.raises(RuntimeError):
        if action == "issue":
            issue(client, headers, data["mouse"], quantity=5)
        else:
            adjust(client, headers, data["mouse"], direction="add", quantity=5)

    assert on_hand(data["mouse"]) == START
    assert movements(data["mouse"]) == [] and audit_rows(data["mouse"]) == []


def test_database_refuses_an_employee_on_a_non_issue_movement(db, manager, data, people):
    user, _ = manager
    item = db.get(StockItem, data["mouse"])
    db.add(StockMovement(
        stock_item_id=item.id, movement_type=MovementType.ADJUSTMENT_IN, quantity=1, balance_after=26,
        movement_date=inventory_service._today(), reason="x", issued_to_employee_id=people["asha"],
        created_by_user_id=user.id,
    ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---- Two at once (C11) ----------------------------------------------------------------------------
def _issue_in_own_session(item_id, user_id, quantity, results, barrier):
    from app.modules.users.models import User

    with SessionLocal() as session:
        actor = session.get(User, user_id)
        barrier.wait()
        try:
            inventory_service.issue_stock(session, actor=actor, item_id=item_id, quantity=quantity, reason="Rush order")
            results.append("ok")
        except AppError as error:
            results.append(error.code)


def test_two_simultaneous_issues_cannot_take_stock_below_zero(manager, data):
    user, _ = manager
    results: list = []
    barrier = threading.Barrier(2)
    threads = [threading.Thread(target=_issue_in_own_session, args=(data["mouse"], user.id, 15, results, barrier)) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == ["insufficient_stock", "ok"]
    assert on_hand(data["mouse"]) == START - 15
    assert len(movements(data["mouse"])) == 1


# ---- Deactivation once stock is 0 (B38) -------------------------------------------------------------
def test_deactivation_works_once_stock_is_zero(client, manager, data):
    _, headers = manager
    refused = client.post(f"{ITEMS}/{data['mouse']}/deactivate", headers=headers)
    assert refused.status_code == 409 and error_code(refused) == "stock_not_zero"

    issue(client, headers, data["mouse"], quantity=START, reason="Moved to branch office")
    done = client.post(f"{ITEMS}/{data['mouse']}/deactivate", headers=headers)

    assert done.status_code == 200 and done.json()["status"] == "inactive"
    after = issue(client, headers, data["mouse"])
    assert after.status_code == 409 and error_code(after) == "stock_item_inactive"


# ---- Roles --------------------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_issue_and_adjust(client, staff_headers, data, role):
    _, headers = staff_headers(role)
    assert issue(client, headers, data["mouse"]).status_code == 200
    assert adjust(client, headers, data["mouse"], direction="add").status_code == 200


def test_employee_role_cannot_issue_or_adjust(client, staff_headers, data):
    _, headers = staff_headers("Employee")
    for response in (issue(client, headers, data["mouse"]), adjust(client, headers, data["mouse"])):
        assert response.status_code == 403 and error_code(response) == "forbidden"
    assert on_hand(data["mouse"]) == START


def test_issue_and_adjust_need_login(client, data):
    assert client.post(f"{ITEMS}/{data['mouse']}/issue", json={"quantity": 1, "reason": "x"}).status_code == 401
    assert client.post(f"{ITEMS}/{data['mouse']}/adjust", json={"direction": "add", "quantity": 1, "reason": "x"}).status_code == 401
