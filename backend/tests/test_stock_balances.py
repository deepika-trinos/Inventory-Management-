"""Stock balances (Slice 4.3: INV-02, INV-05, INV-06; decisions B37, C2-C4, G1, G2).

Reading only: each stock item's low-stock flag (active, quantity on hand at or below the
reorder threshold), the low-stock filter, and each item's movement history.

Done-check (build plan): items at or below their threshold are flagged as low stock."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import MovementType, StockItem, StockMovement
from app.modules.purchases.service import _today
from app.modules.users.models import User
from tests.test_purchases_api import (  # noqa: F401  (pytest fixtures used by name)
    data,
    error_code,
    manager,
    mouse_line,
    staff_headers,
)
from tests.test_receive_bulk import bulk_receipt, make_draft
from tests.test_receive_serialized import receive

ITEMS = "/api/v1/stock-items"


def make_item(client, headers, category_id, name, threshold, on_hand, status="active"):
    """A stock item with this balance (test-only shortcut: the balance is set directly;
    real stock changes come from movements). Returns its id."""
    response = client.post(ITEMS, headers=headers, json={
        "name": name, "category_id": category_id, "unit_of_measure": "pieces", "reorder_threshold": threshold,
    })
    assert response.status_code == 201, response.text
    item_id = response.json()["id"]
    with SessionLocal() as s:
        item = s.get(StockItem, item_id)
        item.quantity_on_hand = on_hand
        item.status = status
        s.commit()
    return item_id


def listed(client, headers, **params):
    response = client.get(ITEMS, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def flags(client, headers, **params):
    return {i["name"]: i["low_stock"] for i in listed(client, headers, **params)["items"]}


@pytest.fixture
def stock(client, manager, data):
    """USB mouse (25 on hand, threshold 5: fine), Old mouse (inactive, 0, threshold 0) from
    the purchases fixture, plus: Below (2 / 5), At (5 / 5), Above (6 / 5),
    Zero-out (0 / 0), Zero-one (1 / 0)."""
    _, headers = manager
    cat = data["peripherals"]
    for name, threshold, on_hand in [("Below", 5, 2), ("At", 5, 5), ("Above", 5, 6), ("Zero-out", 0, 0), ("Zero-one", 0, 1)]:
        make_item(client, headers, cat, name, threshold, on_hand)
    return headers


# ---- Done-check: items at or below their threshold are flagged --------------------------------
def test_items_at_or_below_their_threshold_are_flagged_as_low_stock(client, stock):
    assert flags(client, stock) == {
        "Above": False,
        "At": True,  # at the threshold counts (B37)
        "Below": True,
        "Old mouse": False,  # inactive: never flagged (G1)
        "USB mouse": False,
        "Zero-one": False,  # threshold 0: only warns when stock runs out (B37)
        "Zero-out": True,
    }


def test_one_item_shows_its_low_stock_flag(client, stock):
    items = {i["name"]: i["id"] for i in listed(client, stock)["items"]}

    below = client.get(f"{ITEMS}/{items['Below']}", headers=stock).json()
    above = client.get(f"{ITEMS}/{items['Above']}", headers=stock).json()

    assert (below["low_stock"], below["quantity_on_hand"], below["reorder_threshold"]) == (True, 2, 5)
    assert above["low_stock"] is False


def test_inactive_item_at_zero_is_not_low_stock(client, manager, data):
    _, headers = manager
    make_item(client, headers, data["peripherals"], "Retired cable", 3, 0, status="inactive")
    assert flags(client, headers, status="inactive") == {"Old mouse": False, "Retired cable": False}


def test_flag_follows_the_balance(client, manager, data):
    """A receipt that lifts the balance above the threshold clears the flag."""
    _, headers = manager
    item_id = make_item(client, headers, data["peripherals"], "Keyboard", 5, 1)
    assert client.get(f"{ITEMS}/{item_id}", headers=headers).json()["low_stock"] is True

    purchase = make_draft(client, headers, data, [mouse_line(item_id, quantity=10)])
    assert receive(client, headers, purchase, bulk_receipt(purchase, 10)).status_code == 200

    item = client.get(f"{ITEMS}/{item_id}", headers=headers).json()
    assert (item["quantity_on_hand"], item["low_stock"]) == (11, False)


# ---- Low-stock filter -----------------------------------------------------------------------------
def test_low_stock_filter(client, stock):
    assert [i["name"] for i in listed(client, stock, low_stock="true")["items"]] == ["At", "Below", "Zero-out"]
    assert [i["name"] for i in listed(client, stock, low_stock="false")["items"]] == [
        "Above", "Old mouse", "USB mouse", "Zero-one",
    ]


def test_low_stock_filter_combines_with_search_category_and_status(client, manager, data, stock):
    make_item(client, stock, data["peripherals"], "Below cable", 9, 1)
    assert [i["name"] for i in listed(client, stock, low_stock="true", search="below")["items"]] == ["Below", "Below cable"]
    assert listed(client, stock, low_stock="true", status="inactive")["items"] == []
    assert listed(client, stock, low_stock="true", category_id=data["peripherals"])["total"] == 4


def test_bad_low_stock_value_is_a_validation_error(client, stock):
    response = client.get(ITEMS, headers=stock, params={"low_stock": "maybe"})
    assert response.status_code == 422
    assert error_code(response) == "validation_error"


# ---- Movement history (INV-05) ----------------------------------------------------------------------
def receive_mice(client, headers, data, *quantities, ref="INV-2026-0042", received_date=None):
    lines = [mouse_line(data["mouse"], quantity=q) for q in quantities]
    dated = {"purchase_date": received_date.isoformat()} if received_date else {}  # B58: not before the purchase
    purchase = make_draft(client, headers, data, lines, reference_number=ref, **dated)
    body = bulk_receipt(purchase, *quantities, received_date=received_date)
    response = receive(client, headers, purchase, body)
    assert response.status_code == 200, response.text
    return response.json()


def history(client, headers, item_id, **params):
    response = client.get(f"{ITEMS}/{item_id}/movements", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_history_shows_each_receipt_with_all_details_newest_first(client, manager, data):
    user, headers = manager
    yesterday = _today() - timedelta(days=1)
    first = receive_mice(client, headers, data, 10, ref="A-1", received_date=yesterday)
    second = receive_mice(client, headers, data, 4, ref="A-2")

    page = history(client, headers, data["mouse"])

    assert page["total"] == 2
    newest, oldest = page["items"]
    assert (newest["movement_type"], newest["direction"], newest["quantity"], newest["change"]) == ("receipt", "in", 4, 4)
    assert newest["balance_after"] == 25 + 10 + 4
    assert oldest["balance_after"] == 25 + 10
    assert oldest["movement_date"] == yesterday.isoformat()  # the business date (C2)
    assert newest["movement_date"] == _today().isoformat()
    assert newest["created_by"] == {"id": user.id, "email": user.email}
    assert newest["created_at"] and newest["reason"] is None
    assert newest["reference"] == {
        "purchase_id": second["id"], "purchase_number": second["purchase_number"],
        "purchase_line_id": second["lines"][0]["id"],
    }
    assert oldest["reference"]["purchase_number"] == first["purchase_number"]


def test_two_lines_of_one_receipt_keep_their_order(client, manager, data):
    """C6: one movement per line, saved together; newest first = line 2 before line 1."""
    _, headers = manager
    purchase = receive_mice(client, headers, data, 10, 5)

    items = history(client, headers, data["mouse"])["items"]

    assert [(m["quantity"], m["balance_after"]) for m in items] == [(5, 40), (10, 35)]
    assert [m["reference"]["purchase_line_id"] for m in items] == [purchase["lines"][1]["id"], purchase["lines"][0]["id"]]


def test_outgoing_movements_show_a_negative_change_and_their_reason(client, manager, data, db):
    """Issues and adjustments arrive in Slice 4.4; written here through the shared service."""
    user, headers = manager
    receive_mice(client, headers, data, 10)
    item = db.get(StockItem, data["mouse"])
    actor = db.get(User, user.id)
    inventory_service.record_movement(
        db, item=item, movement_type=MovementType.ADJUSTMENT_OUT, quantity=3, movement_date=_today(),
        actor=actor, reason="Two broken, one lost",
    )
    db.commit()

    newest = history(client, headers, data["mouse"])["items"][0]

    assert (newest["movement_type"], newest["direction"], newest["change"]) == ("adjustment_out", "out", -3)
    assert newest["balance_after"] == 32
    assert newest["reason"] == "Two broken, one lost"
    assert newest["reference"] is None


def test_history_is_paged_without_repeats(client, manager, data):
    _, headers = manager
    for n in range(5):
        receive_mice(client, headers, data, n + 1, ref=f"P-{n}")

    pages = [history(client, headers, data["mouse"], page=p, page_size=2) for p in (1, 2, 3)]

    ids = [m["id"] for p in pages for m in p["items"]]
    assert len(ids) == 5 and len(set(ids)) == 5
    assert ids == sorted(ids, reverse=True)  # newest saved first (G2)
    assert all(p["total"] == 5 for p in pages)


def test_balance_after_of_the_newest_movement_matches_the_balance(client, manager, data):
    _, headers = manager
    receive_mice(client, headers, data, 7)
    receive_mice(client, headers, data, 3, ref="B-2")

    newest = history(client, headers, data["mouse"])["items"][0]
    item = client.get(f"{ITEMS}/{data['mouse']}", headers=headers).json()

    assert newest["balance_after"] == item["quantity_on_hand"] == 35


def test_item_without_movements_has_an_empty_history(client, manager, data):
    _, headers = manager
    assert history(client, headers, data["mouse"]) == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_inactive_item_keeps_its_history(client, manager, data):
    _, headers = manager
    item_id = make_item(client, headers, data["peripherals"], "Webcam", 0, 0)
    purchase = make_draft(client, headers, data, [mouse_line(item_id, quantity=2)])
    receive(client, headers, purchase, bulk_receipt(purchase, 2))
    with SessionLocal() as s:  # back to zero, then deactivated (test-only shortcut; issue is Slice 4.4)
        item = s.get(StockItem, item_id)
        item.quantity_on_hand = 0
        item.status = "inactive"
        s.commit()

    assert history(client, headers, item_id)["total"] == 1


def test_history_of_unknown_item_gives_404(client, manager, data):
    _, headers = manager
    response = client.get(f"{ITEMS}/99999/movements", headers=headers)
    assert response.status_code == 404
    assert error_code(response) == "stock_item_not_found"


def test_reading_changes_nothing(client, manager, data, stock):
    _, headers = manager
    receive_mice(client, headers, data, 4)
    with SessionLocal() as s:
        before = [(i.id, i.quantity_on_hand, i.updated_at) for i in s.scalars(select(StockItem).order_by(StockItem.id))]
        moves_before = len(s.scalars(select(StockMovement)).all())

    listed(client, headers, low_stock="true")
    history(client, headers, data["mouse"])
    client.get(f"{ITEMS}/{data['mouse']}", headers=headers)

    with SessionLocal() as s:
        after = [(i.id, i.quantity_on_hand, i.updated_at) for i in s.scalars(select(StockItem).order_by(StockItem.id))]
        assert len(s.scalars(select(StockMovement)).all()) == moves_before
    assert before == after


# ---- Roles ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_read_balances_and_history(client, staff_headers, data, role):
    _, headers = staff_headers(role)
    assert client.get(ITEMS, headers=headers, params={"low_stock": "true"}).status_code == 200
    assert client.get(f"{ITEMS}/{data['mouse']}/movements", headers=headers).status_code == 200


def test_employee_role_is_blocked(client, staff_headers, data):
    _, headers = staff_headers("Employee")
    for url in (f"{ITEMS}?low_stock=true", f"{ITEMS}/{data['mouse']}/movements"):
        response = client.get(url, headers=headers)
        assert response.status_code == 403 and error_code(response) == "forbidden"


def test_history_needs_login(client, data):
    assert client.get(f"{ITEMS}/{data['mouse']}/movements").status_code == 401
