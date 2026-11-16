"""Receiving by-quantity items and stock movements (Slice 3.3: PUR-07, INV-03, INV-05,
INV-07, BR-09, BR-10, BR-13; decisions P4, P7, B36, B38, B39, B55, B58, C1-C8)."""

import threading
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.modules.assets.models import Asset
from app.modules.audit import service as audit
from app.modules.audit.models import AuditLog
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import MovementType, StockItem, StockMovement
from app.modules.purchases import service
from app.modules.purchases.models import Purchase, PurchaseLine
from app.modules.purchases.service import _today
from tests.test_purchases_api import (  # noqa: F401  (pytest fixtures used by name)
    PURCHASES,
    audit_for,
    create,
    data,
    error_code,
    laptop_line,
    manager,
    mouse_line,
    staff_headers,
    stock_on_hand,
    stock_tables_snapshot,
)
from tests.test_receive_serialized import receive, unit

STOCK_ITEMS = "/api/v1/stock-items"
START = 25  # the data fixture puts 25 USB mice on hand


def make_draft(client, headers, data, lines, **overrides):
    response = create(client, headers, data, lines=lines, **overrides)
    assert response.status_code == 201, response.text
    return response.json()


def bulk_receipt(purchase, *quantities, units=None, received_date=None):
    """Body: quantities[i] for line i. One-by-one lines get `units[i]` (default: none)."""
    units = units or {}
    return {
        "received_date": (received_date or _today()).isoformat(),
        "lines": [
            {"line_id": line["id"], "received_quantity": q, "units": units.get(i, [])}
            for i, (line, q) in enumerate(zip(purchase["lines"], quantities, strict=True))
        ],
    }


def movements(item_id: int | None = None) -> list[StockMovement]:
    with SessionLocal() as fresh:
        stmt = select(StockMovement).order_by(StockMovement.id)
        if item_id is not None:
            stmt = stmt.where(StockMovement.stock_item_id == item_id)
        rows = list(fresh.scalars(stmt).all())
        fresh.expunge_all()
        return rows


def assert_nothing_saved(purchase, stock_before):
    with SessionLocal() as fresh:
        saved = fresh.get(Purchase, purchase["id"])
        assert saved.status == "draft" and saved.received_date is None
        assert all(fresh.get(PurchaseLine, line["id"]).received_quantity is None for line in purchase["lines"])
        assert fresh.scalars(select(Asset)).all() == []
    assert stock_tables_snapshot() == stock_before
    assert audit_for(purchase["id"], "purchase.received") == []


# ---- Done-check: receiving 10 mice adds 10 with exactly one movement -------------------------
def test_receiving_ten_mice_adds_ten_with_exactly_one_movement(client, manager, data):
    user, headers = manager
    purchase = make_draft(client, headers, data, [mouse_line(data["mouse"], quantity=10)])

    response = receive(client, headers, purchase, bulk_receipt(purchase, 10))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "received"
    assert body["lines"][0]["received_quantity"] == 10
    assert body["lines"][0]["stock_item"]["quantity_on_hand"] == START + 10
    assert body["lines"][0]["assets"] == []
    assert stock_on_hand(data["mouse"]) == START + 10

    [movement] = movements()
    assert movement.stock_item_id == data["mouse"]
    assert movement.movement_type == MovementType.RECEIPT
    assert movement.quantity == 10
    assert movement.balance_after == START + 10  # C4
    assert movement.movement_date == _today()  # C2: the received date
    assert movement.created_at is not None
    assert movement.purchase_line_id == purchase["lines"][0]["id"]
    assert movement.created_by_user_id == user.id  # the responsible user (BR-09)
    assert movement.reason is None  # C3: receipts have no reason


def test_movement_date_is_the_received_date_not_the_save_date(client, manager, data):
    _, headers = manager
    earlier = _today() - timedelta(days=5)
    purchase = make_draft(
        client, headers, data, [mouse_line(data["mouse"], quantity=4)], purchase_date=earlier.isoformat()
    )
    received_on = _today() - timedelta(days=2)

    response = receive(client, headers, purchase, bulk_receipt(purchase, 4, received_date=received_on))

    assert response.status_code == 200, response.text
    assert movements()[0].movement_date == received_on


def test_mixed_purchase_of_three_laptops_and_ten_mice(client, manager, data):
    _, headers = manager
    purchase = make_draft(
        client, headers, data, [laptop_line(data["laptops"], quantity=3), mouse_line(data["mouse"], quantity=10)]
    )
    body = bulk_receipt(purchase, 3, 10, units={0: [unit("L-1"), unit("L-2"), unit("L-3")]})

    response = receive(client, headers, purchase, body)

    assert response.status_code == 200, response.text
    lines = response.json()["lines"]
    assert [a["asset_code"] for a in lines[0]["assets"]] == ["AST-000001", "AST-000002", "AST-000003"]
    assert lines[1]["received_quantity"] == 10
    assert stock_on_hand(data["mouse"]) == START + 10
    assert len(movements()) == 1  # the laptops make assets, not movements
    with SessionLocal() as fresh:
        assert fresh.scalar(select(func.count()).select_from(Asset)) == 3


def test_fewer_than_ordered_adds_only_what_arrived(client, manager, data):
    _, headers = manager
    purchase = make_draft(client, headers, data, [mouse_line(data["mouse"], quantity=10)])

    assert receive(client, headers, purchase, bulk_receipt(purchase, 7)).status_code == 200

    assert stock_on_hand(data["mouse"]) == START + 7
    assert movements()[0].quantity == 7


def test_bulk_line_received_as_zero_writes_no_movement(client, manager, data):
    """C1: 0 received closes the line with no movement; the other line still arrives."""
    _, headers = manager
    purchase = make_draft(
        client, headers, data, [laptop_line(data["laptops"], quantity=1), mouse_line(data["mouse"], quantity=10)]
    )

    response = receive(client, headers, purchase, bulk_receipt(purchase, 1, 0, units={0: [unit("L-1")]}))

    assert response.status_code == 200, response.text
    assert response.json()["lines"][1]["received_quantity"] == 0
    assert movements() == []
    assert stock_on_hand(data["mouse"]) == START


def test_zero_on_every_line_is_rejected(client, manager, data):
    _, headers = manager
    purchase = make_draft(client, headers, data, [mouse_line(data["mouse"], quantity=10)])
    before = stock_tables_snapshot()

    response = receive(client, headers, purchase, bulk_receipt(purchase, 0))

    assert response.status_code == 422 and error_code(response) == "nothing_received"
    assert_nothing_saved(purchase, before)


def test_same_item_on_two_lines_gets_one_movement_per_line(client, manager, data):
    """C6: 10 at 300 and 5 at 350 -> two movements, balance +15."""
    _, headers = manager
    purchase = make_draft(
        client, headers, data,
        [mouse_line(data["mouse"], quantity=10, unit_cost="300.00"),
         mouse_line(data["mouse"], quantity=5, unit_cost="350.00")],
    )

    assert receive(client, headers, purchase, bulk_receipt(purchase, 10, 5)).status_code == 200

    rows = movements()
    assert [(m.quantity, m.balance_after) for m in rows] == [(10, START + 10), (5, START + 15)]
    assert [m.purchase_line_id for m in rows] == [line["id"] for line in purchase["lines"]]
    assert stock_on_hand(data["mouse"]) == START + 15


# ---- Refusals: nothing is saved -------------------------------------------------------------
def test_more_than_ordered_is_rejected(client, manager, data):
    _, headers = manager
    purchase = make_draft(client, headers, data, [mouse_line(data["mouse"], quantity=10)])
    before = stock_tables_snapshot()

    response = receive(client, headers, purchase, bulk_receipt(purchase, 11))

    assert response.status_code == 422 and error_code(response) == "received_quantity_too_high"
    assert response.json()["error"]["details"]["line"] == 1
    assert_nothing_saved(purchase, before)


def test_bulk_line_takes_no_unit_details(client, manager, data):
    _, headers = manager
    purchase = make_draft(client, headers, data, [mouse_line(data["mouse"], quantity=2)])
    before = stock_tables_snapshot()

    response = receive(client, headers, purchase, bulk_receipt(purchase, 2, units={0: [unit("X-1"), unit("X-2")]}))

    assert response.status_code == 422 and error_code(response) == "units_not_allowed"
    assert_nothing_saved(purchase, before)


def test_deactivated_stock_item_refuses_the_receipt(client, manager, data, db):
    """C5: stock may not arrive on an inactive item (keeps B38: inactive = zero stock)."""
    _, headers = manager
    pencil = inventory_service.create_stock_item(
        db, name="Pencil", category_id=data["peripherals"], unit_of_measure="boxes", reorder_threshold=0
    )
    purchase = make_draft(
        client, headers, data, [laptop_line(data["laptops"], quantity=1), mouse_line(pencil.id, quantity=3)]
    )
    inventory_service.set_active(db, actor=None, item=pencil, active=False)
    before = stock_tables_snapshot()

    response = receive(client, headers, purchase, bulk_receipt(purchase, 1, 3, units={0: [unit("L-1")]}))

    assert response.status_code == 409 and error_code(response) == "stock_item_inactive"
    assert response.json()["error"]["details"]["line"] == 2
    assert "Reactivate" in response.json()["error"]["message"]
    assert_nothing_saved(purchase, before)


def test_deactivated_stock_item_with_zero_received_does_not_block(client, manager, data, db):
    """Nothing arrives for the inactive item, so B38 still holds: the receipt goes through."""
    _, headers = manager
    pencil = inventory_service.create_stock_item(
        db, name="Pencil", category_id=data["peripherals"], unit_of_measure="boxes", reorder_threshold=0
    )
    purchase = make_draft(
        client, headers, data, [mouse_line(data["mouse"], quantity=2), mouse_line(pencil.id, quantity=3)]
    )
    inventory_service.set_active(db, actor=None, item=pencil, active=False)

    response = receive(client, headers, purchase, bulk_receipt(purchase, 2, 0))

    assert response.status_code == 200, response.text
    assert stock_on_hand(pencil.id) == 0


def test_bad_serial_on_the_laptop_line_also_keeps_the_mice_out(client, manager, data):
    _, headers = manager
    purchase = make_draft(
        client, headers, data, [laptop_line(data["laptops"], quantity=2), mouse_line(data["mouse"], quantity=10)]
    )
    before = stock_tables_snapshot()

    response = receive(client, headers, purchase, bulk_receipt(purchase, 2, 10, units={0: [unit("D-1"), unit("d-1")]}))

    assert response.status_code == 409 and error_code(response) == "serial_number_duplicate"
    assert_nothing_saved(purchase, before)


def test_forced_error_mid_receipt_saves_nothing(db, data, make_user, monkeypatch):
    """The audit write fails after the movement and balance change: all of it is undone."""
    user, _ = make_user("IT Manager")
    purchase = service.create_purchase(
        db,
        data={"vendor_id": data["acme"], "reference_number": "ERR-1", "purchase_date": _today(),
              "lines": [laptop_line(data["laptops"], quantity=1), mouse_line(data["mouse"], quantity=10)]},
        actor=user,
    )
    purchase = service.get_purchase(db, purchase.id, lock=True)
    before = stock_tables_snapshot()
    real_record = audit.record

    def failing_record(*args, **kwargs):
        if kwargs.get("action") == "purchase.received":
            raise RuntimeError("disk full")
        return real_record(*args, **kwargs)

    monkeypatch.setattr(audit, "record", failing_record)
    with pytest.raises(RuntimeError):
        service.receive_purchase(
            db, actor=user, purchase=purchase,
            data={"received_date": _today(), "lines": [
                {"line_id": purchase.lines[0].id, "received_quantity": 1, "units": [unit("S-1")]},
                {"line_id": purchase.lines[1].id, "received_quantity": 10, "units": []},
            ]},
        )

    assert stock_tables_snapshot() == before  # balance and movement count unchanged
    with SessionLocal() as fresh:
        assert fresh.get(Purchase, purchase.id).status == "draft"
        assert fresh.scalars(select(Asset)).all() == []
        assert fresh.scalars(select(AuditLog).where(AuditLog.action == "purchase.received")).all() == []


# ---- Two receipts at the same moment ------------------------------------------------------------
def _receive_bulk_in_own_session(purchase_id, user_id, quantity, results, barrier):
    with SessionLocal() as session:
        from app.modules.users.models import User

        actor = session.get(User, user_id)
        barrier.wait()
        try:
            purchase = service.get_purchase(session, purchase_id, lock=True)
            service.receive_purchase(
                session, actor=actor, purchase=purchase,
                data={"received_date": _today(), "lines": [
                    {"line_id": purchase.lines[0].id, "received_quantity": quantity, "units": []},
                ]},
            )
            results.append("ok")
        except AppError as error:
            results.append(error.code)


def test_receipts_at_the_same_moment_give_the_right_total(db, data, make_user):
    user, _ = make_user("IT Manager")
    quantities = [3, 4, 5, 6]
    drafts = [
        service.create_purchase(
            db,
            data={"vendor_id": data["acme"], "reference_number": f"PAR-{q}", "purchase_date": _today(),
                  "lines": [mouse_line(data["mouse"], quantity=q)]},
            actor=user,
        ).id
        for q in quantities
    ]
    results: list = []
    barrier = threading.Barrier(len(drafts))
    threads = [
        threading.Thread(target=_receive_bulk_in_own_session, args=(pid, user.id, q, results, barrier))
        for pid, q in zip(drafts, quantities, strict=True)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert results == ["ok"] * len(drafts)
    assert stock_on_hand(data["mouse"]) == START + sum(quantities)
    rows = movements()
    assert len(rows) == len(drafts)
    # Each movement's balance_after is the running total, in the order they were saved.
    running = START
    for m in rows:
        running += m.quantity
        assert m.balance_after == running


def test_the_same_draft_received_twice_at_once_counts_once(db, data, make_user):
    user, _ = make_user("IT Manager")
    pid = service.create_purchase(
        db,
        data={"vendor_id": data["acme"], "reference_number": "TWICE", "purchase_date": _today(),
              "lines": [mouse_line(data["mouse"], quantity=10)]},
        actor=user,
    ).id
    results: list = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_receive_bulk_in_own_session, args=(pid, user.id, 10, results, barrier))
        for _ in range(2)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert sorted(results) == ["ok", "purchase_not_draft"]
    assert stock_on_hand(data["mouse"]) == START + 10
    assert len(movements()) == 1


# ---- Audit (BR-13; no audit row per movement) ------------------------------------------------
def test_purchase_received_lists_the_bulk_receipts_and_no_movement_audit_rows(client, manager, data):
    _, headers = manager
    purchase = make_draft(
        client, headers, data, [laptop_line(data["laptops"], quantity=1), mouse_line(data["mouse"], quantity=10)]
    )

    with SessionLocal() as fresh:
        last_before = fresh.scalar(select(func.max(AuditLog.id)))

    assert receive(client, headers, purchase, bulk_receipt(purchase, 1, 10, units={0: [unit("L-1")]})).status_code == 200

    [entry] = audit_for(purchase["id"], "purchase.received")
    assert entry.after_data["stock_received"] == [
        {"stock_item_id": data["mouse"], "stock_item": "USB mouse", "unit_of_measure": "pieces",
         "received_quantity": 10, "balance_after": START + 10},
    ]
    assert entry.after_data["lines"][1]["received_quantity"] == 10
    assert "stock_received" not in entry.before_data
    with SessionLocal() as fresh:
        written = list(fresh.scalars(select(AuditLog.action).where(AuditLog.id > last_before).order_by(AuditLog.id)))
    # Exactly these rows: no audit row per movement (the movement table is the history).
    assert written == ["purchase.received", "asset.created"]


# ---- Movements are append-only ------------------------------------------------------------------
@pytest.fixture
def one_movement(client, manager, data):
    _, headers = manager
    purchase = make_draft(client, headers, data, [mouse_line(data["mouse"], quantity=10)])
    assert receive(client, headers, purchase, bulk_receipt(purchase, 10)).status_code == 200
    return movements()[0].id


def test_movement_cannot_be_changed_through_the_orm(db, one_movement):
    movement = db.get(StockMovement, one_movement)
    movement.quantity = 99
    with pytest.raises(PermissionError):
        db.flush()
    db.rollback()


def test_movement_cannot_be_deleted_through_the_orm(db, one_movement):
    db.delete(db.get(StockMovement, one_movement))
    with pytest.raises(PermissionError):
        db.flush()
    db.rollback()


@pytest.mark.parametrize(
    "sql",
    ["UPDATE stock_movements SET quantity = 99 WHERE id = :id", "DELETE FROM stock_movements WHERE id = :id"],
)
def test_database_trigger_blocks_update_and_delete(db, one_movement, sql):
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text(sql), {"id": one_movement})
    db.rollback()
    assert movements()[0].quantity == 10


@pytest.mark.parametrize(
    "values",
    [
        {"quantity": 0},  # quantity > 0
        {"balance_after": -1},  # balance never negative
        {"movement_type": "gift"},  # P7 list only
        {"purchase_line_id": None},  # a receipt must name its purchase line
    ],
)
def test_database_checks_on_movements(db, one_movement, values):
    row = {
        "stock_item_id": 1, "movement_type": "receipt", "quantity": 1, "balance_after": 1,
        "movement_date": _today(), "purchase_line_id": 1, "created_by_user_id": 1,
    }
    row.update(values)
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO stock_movements (stock_item_id, movement_type, quantity, balance_after, movement_date, "
                "purchase_line_id, created_by_user_id) VALUES (:stock_item_id, :movement_type, :quantity, "
                ":balance_after, :movement_date, :purchase_line_id, :created_by_user_id)"
            ),
            row,
        )
    db.rollback()


# ---- record_movement(): the one shared way to change stock ---------------------------------------
@pytest.fixture
def mouse(db, data):
    items = inventory_service.lock_stock_items(db, [data["mouse"]])
    return items[data["mouse"]]


@pytest.mark.parametrize("kind", [MovementType.ISSUE, MovementType.ADJUSTMENT_OUT])
def test_out_movement_never_takes_stock_below_zero(db, data, make_user, mouse, kind):
    """C7 / INV-07 / BR-10: 25 on hand, 26 requested -> insufficient_stock, nothing changes."""
    user, _ = make_user("IT Manager")
    with pytest.raises(AppError) as caught:
        inventory_service.record_movement(
            db, item=mouse, movement_type=kind, quantity=START + 1, movement_date=_today(), actor=user,
        )
    assert caught.value.code == "insufficient_stock"
    assert caught.value.status_code == 409
    assert caught.value.details == {"stock_item_id": data["mouse"], "quantity_on_hand": START, "requested": START + 1}
    assert f"Only {START} pieces" in caught.value.message
    db.rollback()
    assert stock_on_hand(data["mouse"]) == START and movements() == []


def test_out_movement_down_to_exactly_zero_is_allowed(db, data, make_user, mouse):
    user, _ = make_user("IT Manager")
    movement = inventory_service.record_movement(
        db, item=mouse, movement_type=MovementType.ISSUE, quantity=START, movement_date=_today(), actor=user,
    )
    db.commit()
    assert movement.balance_after == 0 and stock_on_hand(data["mouse"]) == 0


@pytest.mark.parametrize("kind", [MovementType.ADJUSTMENT_IN, MovementType.OPENING])
def test_other_in_movements_raise_the_balance(db, data, make_user, mouse, kind):
    user, _ = make_user("IT Manager")
    inventory_service.record_movement(
        db, item=mouse, movement_type=kind, quantity=5, movement_date=_today(), actor=user, reason="  count  "
    )
    db.commit()
    [row] = movements()
    assert row.balance_after == START + 5 and row.reason == "count"  # reason trimmed
    assert row.purchase_line_id is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"movement_type": "gift", "quantity": 1},
        {"movement_type": MovementType.ISSUE, "quantity": 0},
        {"movement_type": MovementType.ISSUE, "quantity": -3},
        {"movement_type": MovementType.RECEIPT, "quantity": 1},  # a receipt needs its purchase line
        {"movement_type": MovementType.ISSUE, "quantity": 1, "purchase_line_id": 1},  # only receipts have one
    ],
)
def test_record_movement_refuses_programming_mistakes(db, make_user, mouse, kwargs):
    user, _ = make_user("IT Manager")
    with pytest.raises(ValueError):
        inventory_service.record_movement(db, item=mouse, movement_date=_today(), actor=user, **kwargs)
    db.rollback()


def test_reason_longer_than_500_characters_is_refused(db, make_user, mouse):
    user, _ = make_user("IT Manager")
    with pytest.raises(AppError) as caught:
        inventory_service.record_movement(
            db, item=mouse, movement_type=MovementType.ADJUSTMENT_IN, quantity=1,
            movement_date=_today(), actor=user, reason="x" * 501,
        )
    assert caught.value.code == "invalid_reason"
    db.rollback()


# ---- Unit lock (B36) and deactivate only at zero (B38) -----------------------------------------
def test_unit_locks_after_a_receipt(client, manager, data):
    _, headers = manager
    purchase = make_draft(client, headers, data, [mouse_line(data["mouse"], quantity=2)])
    assert receive(client, headers, purchase, bulk_receipt(purchase, 2)).status_code == 200

    response = client.patch(f"{STOCK_ITEMS}/{data['mouse']}", headers=headers, json={"unit_of_measure": "boxes"})

    assert response.status_code == 409 and error_code(response) == "unit_locked"
    # Name and threshold stay editable.
    ok = client.patch(f"{STOCK_ITEMS}/{data['mouse']}", headers=headers, json={"reorder_threshold": 8})
    assert ok.status_code == 200, ok.text


def test_unit_stays_locked_when_the_balance_is_back_to_zero(db, client, manager, data, make_user):
    """History counts, not just the balance: 10 boxes must never silently become 10 pieces."""
    user, headers = manager
    cable = inventory_service.create_stock_item(
        db, name="HDMI cable", category_id=data["peripherals"], unit_of_measure="pieces", reorder_threshold=0
    )
    purchase = make_draft(client, headers, data, [mouse_line(cable.id, quantity=3)])
    assert receive(client, headers, purchase, bulk_receipt(purchase, 3)).status_code == 200
    db.expire_all()
    item = inventory_service.lock_stock_items(db, [cable.id])[cable.id]
    inventory_service.record_movement(
        db, item=item, movement_type=MovementType.ISSUE, quantity=3, movement_date=_today(), actor=user
    )
    db.commit()
    assert stock_on_hand(cable.id) == 0

    response = client.patch(f"{STOCK_ITEMS}/{cable.id}", headers=headers, json={"unit_of_measure": "boxes"})

    assert response.status_code == 409 and error_code(response) == "unit_locked"


def test_unit_can_still_change_before_any_stock(client, manager, data, db):
    _, headers = manager
    cable = inventory_service.create_stock_item(
        db, name="HDMI cable", category_id=data["peripherals"], unit_of_measure="pieces", reorder_threshold=0
    )
    response = client.patch(f"{STOCK_ITEMS}/{cable.id}", headers=headers, json={"unit_of_measure": "boxes"})
    assert response.status_code == 200, response.text


def test_item_with_received_stock_cannot_be_deactivated_until_zero(db, client, manager, data):
    user, headers = manager
    cable = inventory_service.create_stock_item(
        db, name="HDMI cable", category_id=data["peripherals"], unit_of_measure="pieces", reorder_threshold=0
    )
    purchase = make_draft(client, headers, data, [mouse_line(cable.id, quantity=3)])
    assert receive(client, headers, purchase, bulk_receipt(purchase, 3)).status_code == 200

    refused = client.post(f"{STOCK_ITEMS}/{cable.id}/deactivate", headers=headers)
    assert refused.status_code == 409 and error_code(refused) == "stock_not_zero"

    db.expire_all()
    item = inventory_service.lock_stock_items(db, [cable.id])[cable.id]
    inventory_service.record_movement(
        db, item=item, movement_type=MovementType.ISSUE, quantity=3, movement_date=_today(), actor=user
    )
    db.commit()
    allowed = client.post(f"{STOCK_ITEMS}/{cable.id}/deactivate", headers=headers)
    assert allowed.status_code == 200, allowed.text


# ---- Roles (P6) ---------------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_receive_bulk(client, staff_headers, data, role):
    _, headers = staff_headers(role)
    purchase = make_draft(client, headers, data, [mouse_line(data["mouse"], quantity=2)])
    assert receive(client, headers, purchase, bulk_receipt(purchase, 2)).status_code == 200
    assert stock_on_hand(data["mouse"]) == START + 2


def test_employee_cannot_receive_bulk(client, staff_headers, manager, data):
    _, manager_headers = manager
    purchase = make_draft(client, manager_headers, data, [mouse_line(data["mouse"], quantity=2)])
    before = stock_tables_snapshot()
    _, employee = staff_headers("Employee")

    response = receive(client, employee, purchase, bulk_receipt(purchase, 2))

    assert response.status_code == 403 and error_code(response) == "forbidden"
    assert_nothing_saved(purchase, before)


def test_receive_bulk_needs_login(client, manager, data):
    _, headers = manager
    purchase = make_draft(client, headers, data, [mouse_line(data["mouse"], quantity=2)])
    response = receive(client, {}, purchase, bulk_receipt(purchase, 2))
    assert response.status_code == 401
    assert stock_on_hand(data["mouse"]) == START


def test_stock_item_balance_is_shown_on_purchase_lines(client, manager, data):
    """C8: the receive screen shows 'in stock now', so the line carries the current balance."""
    _, headers = manager
    purchase = make_draft(client, headers, data, [mouse_line(data["mouse"], quantity=2)])
    assert purchase["lines"][0]["stock_item"]["quantity_on_hand"] == START


def test_balance_always_matches_the_movement_history(db, data, make_user, mouse):
    """B39: after any movement the stored balance equals START plus the movement totals."""
    user, _ = make_user("IT Manager")
    for kind, q in [(MovementType.ADJUSTMENT_IN, 4), (MovementType.ISSUE, 9), (MovementType.OPENING, 2)]:
        inventory_service.record_movement(db, item=mouse, movement_type=kind, quantity=q, movement_date=_today(), actor=user)
    db.commit()
    rows = movements(data["mouse"])
    signed = sum(m.quantity if m.movement_type in MovementType.INCOMING else -m.quantity for m in rows)
    with SessionLocal() as fresh:
        assert fresh.get(StockItem, data["mouse"]).quantity_on_hand == START + signed == rows[-1].balance_after
