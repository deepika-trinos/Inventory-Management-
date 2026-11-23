"""Existing equipment (Slice 4.5: AST-01, INV-01, PRD question 4; owner's answers A6, A7;
decisions in decisions.md section 25).

- POST /assets: enter an asset the company already owns, without a purchase. Same asset
  ID sequence and serial check as receiving; active one-by-one categories only; always
  Available; no purchase link or vendor.
- PATCH /assets/{ref}: on assets entered by hand, category, purchase date and cost can
  also be changed; received assets keep them locked.
- POST /stock-items/{id}/opening-stock: once per item, only while it has no movements.
- Every save writes its audit row in the same transaction; a failure saves nothing.

Done-check (build plan): an existing laptop and existing cable stock can be entered
without a purchase."""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.modules.assets.models import Asset
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditLog
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import StockItem, StockMovement
from tests.test_asset_register import receive_laptops
from tests.test_purchases_api import (  # noqa: F401  (pytest fixtures used by name)
    data,
    error_code,
    manager,
    staff_headers,
)
from tests.test_receive_serialized import unit

ASSETS = "/api/v1/assets"
ITEMS = "/api/v1/stock-items"


def today():
    return inventory_service._today()


def laptop(**overrides):
    body = {
        "category_id": None,  # filled in by enter()
        "serial_number": "OLD-5001",
        "model": "Latitude 7490",
        "name": "Dell Latitude 7490",
    }
    body.update(overrides)
    return body


def enter(client, headers, data, **overrides):
    body = laptop(**overrides)
    if body.get("category_id") is None and "category_id" not in overrides:
        body["category_id"] = data["laptops"]
    return client.post(ASSETS, headers=headers, json=body)


def asset_count() -> int:
    with SessionLocal() as s:
        return s.scalar(select(func.count(Asset.id)))


def asset_audit(asset_id: int, action: str | None = None) -> list[AuditLog]:
    with SessionLocal() as s:
        stmt = select(AuditLog).where(AuditLog.entity_type == "assets", AuditLog.entity_id == str(asset_id))
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return list(s.scalars(stmt.order_by(AuditLog.id)))


def all_asset_created_rows() -> list[AuditLog]:
    with SessionLocal() as s:
        return list(s.scalars(select(AuditLog).where(AuditLog.action == "asset.created")))


@pytest.fixture
def cable(db, data):
    """HDMI cable: active, 0 on hand, no movements (Peripherals, by quantity)."""
    item = inventory_service.create_stock_item(
        db, name="HDMI cable", category_id=data["peripherals"], unit_of_measure="pieces", reorder_threshold=5
    )
    return item.id


def opening(client, headers, item_id, **body):
    body = {"quantity": 40, **body}
    return client.post(f"{ITEMS}/{item_id}/opening-stock", headers=headers, json=body)


def movements(item_id: int) -> list[StockMovement]:
    with SessionLocal() as s:
        return list(s.scalars(select(StockMovement).where(StockMovement.stock_item_id == item_id).order_by(StockMovement.id)))


def on_hand(item_id: int) -> int:
    with SessionLocal() as s:
        return s.get(StockItem, item_id).quantity_on_hand


def opening_audit(item_id: int) -> list[AuditLog]:
    with SessionLocal() as s:
        stmt = select(AuditLog).where(
            AuditLog.entity_type == "stock_items", AuditLog.entity_id == str(item_id), AuditLog.action == "stock.opening"
        )
        return list(s.scalars(stmt.order_by(AuditLog.id)))


# ---- Done-check ----------------------------------------------------------------------------------
def test_an_existing_laptop_and_existing_cable_stock_can_be_entered_without_a_purchase(client, manager, data, cable):
    _, headers = manager

    laptop_response = enter(client, headers, data)
    cable_response = opening(client, headers, cable, quantity=40)

    assert laptop_response.status_code == 201, laptop_response.text
    asset = laptop_response.json()
    assert asset["asset_code"] == "AST-000001"
    assert asset["status"] == "available"
    assert asset["purchase"] is None
    assert cable_response.status_code == 200, cable_response.text
    assert cable_response.json()["item"]["quantity_on_hand"] == 40
    assert cable_response.json()["movement"]["movement_type"] == "opening"


# ---- Manual asset entry --------------------------------------------------------------------------
def test_entered_asset_saves_all_details_and_trims_text(client, manager, data):
    user, headers = manager
    response = enter(
        client, headers, data, serial_number="  OLD-5001 ", model=" Latitude 7490 ", name=" Finance laptop ",
        brand=" Dell ", location=" Pune office ", purchase_date="2023-04-01", warranty_expiry="2026-04-01",
        cost="64999.50",
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["serial_number"], body["model"], body["name"], body["brand"], body["location"]) == (
        "OLD-5001", "Latitude 7490", "Finance laptop", "Dell", "Pune office",
    )
    assert (body["purchase_date"], body["warranty_expiry"]) == ("2023-04-01", "2026-04-01")
    assert Decimal(str(body["cost"])) == Decimal("64999.50")
    assert body["category"]["id"] == data["laptops"]
    with SessionLocal() as s:
        stored = s.scalars(select(Asset).where(Asset.asset_code == "AST-000001")).one()
        assert stored.purchase_line_id is None and stored.created_by_user_id == user.id


def test_only_the_required_fields_are_enough(client, manager, data):
    _, headers = manager
    response = enter(client, headers, data)
    assert response.status_code == 201
    body = response.json()
    assert body["brand"] is None and body["location"] is None and body["warranty_expiry"] is None
    assert body["purchase_date"] is None and body["cost"] is None


@pytest.mark.parametrize(
    "field, value, code",
    [
        ("serial_number", None, "invalid_serial_number"),
        ("serial_number", "   ", "invalid_serial_number"),
        ("model", None, "invalid_model"),
        ("model", "", "invalid_model"),
        ("name", None, "invalid_asset_name"),
        ("name", "  ", "invalid_asset_name"),
        ("serial_number", "S" * 101, "invalid_serial_number"),
    ],
)
def test_required_fields(client, manager, data, field, value, code):
    _, headers = manager
    response = enter(client, headers, data, **{field: value})
    assert response.status_code == 422 and error_code(response) == code
    assert asset_count() == 0 and all_asset_created_rows() == []


def test_category_is_required(client, manager, data):
    _, headers = manager
    body = laptop(category_id=data["laptops"])
    del body["category_id"]
    response = client.post(ASSETS, headers=headers, json=body)
    assert response.status_code == 422 and error_code(response) == "validation_error"


def test_duplicate_serial_is_refused_in_any_case(client, manager, data):
    _, headers = manager
    receive_laptops(client, headers, data, [unit("DL-1001"), unit("DL-1002")])
    response = enter(client, headers, data, serial_number="dl-1001")
    assert response.status_code == 409 and error_code(response) == "serial_number_taken"
    assert asset_count() == 2

    assert enter(client, headers, data, serial_number="OLD-1").status_code == 201
    again = enter(client, headers, data, serial_number="old-1")
    assert again.status_code == 409 and error_code(again) == "serial_number_taken"


def test_a_category_tracked_by_quantity_is_refused(client, manager, data):
    _, headers = manager
    response = enter(client, headers, data, category_id=data["peripherals"])
    assert response.status_code == 409 and error_code(response) == "category_not_serialized"
    assert asset_count() == 0


def test_an_inactive_category_is_refused(client, manager, data):
    _, headers = manager
    response = enter(client, headers, data, category_id=data["old_laptops"])
    assert response.status_code == 409 and error_code(response) == "category_inactive"


def test_an_unknown_category_is_404(client, manager, data):
    _, headers = manager
    response = enter(client, headers, data, category_id=99999)
    assert response.status_code == 404 and error_code(response) == "category_not_found"


def test_asset_ids_continue_the_same_sequence_as_receiving(client, manager, data):
    _, headers = manager
    receive_laptops(client, headers, data, [unit("DL-1001"), unit("DL-1002")])
    first = enter(client, headers, data, serial_number="OLD-1").json()["asset_code"]
    receive_laptops(client, headers, data, [unit("DL-1003")], reference="INV-2026-0043")
    second = enter(client, headers, data, serial_number="OLD-2").json()["asset_code"]
    assert (first, second) == ("AST-000003", "AST-000005")


def test_purchase_date_today_or_earlier_and_never_future(client, manager, data):
    _, headers = manager
    assert enter(client, headers, data, serial_number="A", purchase_date=today().isoformat()).status_code == 201
    future = enter(client, headers, data, serial_number="B", purchase_date=(today() + timedelta(days=1)).isoformat())
    assert future.status_code == 422 and error_code(future) == "purchase_date_in_future"
    assert asset_count() == 1


def test_warranty_cannot_be_before_the_purchase_date(client, manager, data):
    _, headers = manager
    response = enter(client, headers, data, purchase_date="2023-04-01", warranty_expiry="2023-03-31")
    assert response.status_code == 422 and error_code(response) == "invalid_warranty_expiry"
    assert enter(client, headers, data, warranty_expiry="2020-01-01").status_code == 201  # no purchase date: any warranty


@pytest.mark.parametrize("cost", ["-1", "1.234", "10000000000.00", "abc"])
def test_cost_is_zero_or_more_with_two_decimals(client, manager, data, cost):
    _, headers = manager
    response = enter(client, headers, data, cost=cost)
    assert response.status_code == 422 and error_code(response) == "validation_error"


def test_cost_zero_is_allowed(client, manager, data):
    _, headers = manager
    assert enter(client, headers, data, cost="0").status_code == 201


@pytest.mark.parametrize("extra", [{"status": "assigned"}, {"vendor_id": 1}, {"purchase_line_id": 1}, {"asset_code": "AST-1"}, {"quantity": 2}])
def test_status_vendor_purchase_and_quantity_cannot_be_sent(client, manager, data, extra):
    _, headers = manager
    response = enter(client, headers, data, **extra)
    assert response.status_code == 422 and error_code(response) == "validation_error"
    assert asset_count() == 0


def test_entry_writes_one_asset_created_audit_row(client, manager, data):
    user, headers = manager
    body = enter(client, headers, data, cost="100.00", purchase_date="2024-01-02").json()
    [row] = asset_audit(body["id"])
    assert row.action == "asset.created" and row.actor_user_id == user.id
    assert row.after_data["asset_code"] == body["asset_code"]
    assert row.after_data["purchase_number"] is None and row.after_data["purchase_line_id"] is None
    assert row.after_data["serial_number"] == "OLD-5001" and row.after_data["status"] == "available"


def test_history_shows_the_entry_without_a_purchase(client, manager, data):
    _, headers = manager
    code = enter(client, headers, data).json()["asset_code"]
    [entry] = client.get(f"{ASSETS}/{code}/history", headers=headers).json()["items"]
    assert entry["action"] == "asset.created"


def test_a_failing_audit_row_saves_nothing(client, manager, data, monkeypatch):
    _, headers = manager

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(audit_service, "record", broken_record)
    with pytest.raises(RuntimeError):
        enter(client, headers, data)
    assert asset_count() == 0


# ---- Editing manual assets (I4) ------------------------------------------------------------------
@pytest.fixture
def manual(client, manager, data, db):
    """AST-000001 entered by hand (purchase date 2023-04-01, cost 50000.00) and a second
    one-by-one category, Desktops."""
    from app.modules.categories import service as categories_service

    _, headers = manager
    desktops = categories_service.create_category(db, name="Desktops", tracking_type="serialized")
    response = enter(client, headers, data, purchase_date="2023-04-01", cost="50000.00", warranty_expiry="2026-04-01")
    assert response.status_code == 201
    return {"headers": headers, "code": response.json()["asset_code"], "id": response.json()["id"], "desktops": desktops.id}


def edit(client, headers, code, **body):
    return client.patch(f"{ASSETS}/{code}", headers=headers, json=body)


def test_manual_asset_category_purchase_date_and_cost_can_be_changed_and_audited(client, manual):
    response = edit(client, manual["headers"], manual["code"], category_id=manual["desktops"], purchase_date="2023-03-01", cost="45000.00")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category"]["id"] == manual["desktops"]
    assert body["purchase_date"] == "2023-03-01" and Decimal(str(body["cost"])) == Decimal("45000.00")
    [row] = asset_audit(manual["id"], "asset.updated")
    assert set(row.after_data) == {"category_id", "category", "purchase_date", "cost"}
    assert (row.before_data["category"], row.after_data["category"]) == ("Laptops", "Desktops")


def test_manual_asset_purchase_date_and_cost_can_be_cleared(client, manual):
    response = edit(client, manual["headers"], manual["code"], purchase_date=None, cost=None)
    assert response.status_code == 200
    assert response.json()["purchase_date"] is None and response.json()["cost"] is None


@pytest.mark.parametrize(
    "body, status, code",
    [
        ({"category_id": "peripherals"}, 409, "category_not_serialized"),
        ({"category_id": "old_laptops"}, 409, "category_inactive"),
        ({"category_id": 99999}, 404, "category_not_found"),
        ({"category_id": None}, 422, "validation_error"),
        ({"purchase_date": "future"}, 422, "purchase_date_in_future"),
        ({"purchase_date": "2026-05-01"}, 422, "invalid_warranty_expiry"),  # after the 2026-04-01 warranty
        ({"cost": "-5"}, 422, "validation_error"),
    ],
)
def test_manual_asset_edit_rules(client, manual, data, body, status, code):
    key, value = next(iter(body.items()))
    if value in ("peripherals", "old_laptops"):
        value = data[value]
    if value == "future":
        value = (today() + timedelta(days=1)).isoformat()
    response = edit(client, manual["headers"], manual["code"], **{key: value})
    assert response.status_code == status and error_code(response) == code
    assert asset_audit(manual["id"], "asset.updated") == []


def test_moving_the_purchase_date_and_warranty_together_is_checked_on_the_final_values(client, manual):
    response = edit(client, manual["headers"], manual["code"], purchase_date="2026-05-01", warranty_expiry="2029-05-01")
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("body", [{"category_id": 1}, {"purchase_date": "2026-01-01"}, {"cost": "1.00"}])
def test_received_assets_keep_category_purchase_date_and_cost_locked(client, manager, data, body):
    _, headers = manager
    receive_laptops(client, headers, data, [unit("DL-1001")])
    response = edit(client, headers, "AST-000001", **body)
    assert response.status_code == 422 and error_code(response) == "validation_error"


# ---- Opening stock (A6) --------------------------------------------------------------------------
def test_opening_stock_saves_the_movement_and_audit_row(client, manager, cable):
    user, headers = manager
    response = opening(client, headers, cable, quantity=40, note="  Counted in the store room  ", movement_date="2026-11-01")
    assert response.status_code == 200, response.text
    movement = response.json()["movement"]
    assert movement["movement_type"] == "opening" and movement["quantity"] == 40 and movement["balance_after"] == 40
    assert movement["reason"] == "Counted in the store room" and movement["movement_date"] == "2026-11-01"
    assert on_hand(cable) == 40
    [row] = opening_audit(cable)
    assert row.actor_user_id == user.id
    assert row.before_data == {"quantity_on_hand": 0}
    assert row.after_data["quantity_on_hand"] == 40 and row.after_data["movement_type"] == "opening"
    assert row.after_data["movement_id"] == movement["id"]


def test_opening_stock_note_is_optional_and_date_defaults_to_today(client, manager, cable):
    _, headers = manager
    movement = opening(client, headers, cable, quantity=3).json()["movement"]
    assert movement["reason"] is None and movement["movement_date"] == today().isoformat()


def test_opening_stock_is_allowed_once_only(client, manager, cable):
    _, headers = manager
    assert opening(client, headers, cable).status_code == 200
    again = opening(client, headers, cable, quantity=5)
    assert again.status_code == 409 and error_code(again) == "opening_stock_not_allowed"
    assert on_hand(cable) == 40 and len(movements(cable)) == 1 and len(opening_audit(cable)) == 1


@pytest.mark.parametrize("first", ["adjust", "receive"])
def test_opening_stock_is_blocked_after_any_movement(client, manager, data, cable, first):
    _, headers = manager
    if first == "adjust":
        assert client.post(f"{ITEMS}/{cable}/adjust", headers=headers, json={"direction": "add", "quantity": 2, "reason": "Found"}).status_code == 200
    else:
        from tests.test_purchases_api import mouse_line
        from tests.test_receive_bulk import bulk_receipt, make_draft
        from tests.test_receive_serialized import receive

        purchase = make_draft(client, headers, data, [mouse_line(cable, quantity=4)])
        received = receive(client, headers, purchase, bulk_receipt(purchase, 4))
        assert received.status_code == 200, received.text
    response = opening(client, headers, cable)
    assert response.status_code == 409 and error_code(response) == "opening_stock_not_allowed"
    assert opening_audit(cable) == []


def test_opening_stock_on_an_inactive_item_is_refused(client, manager, data):
    _, headers = manager
    response = opening(client, headers, data["old_mouse"])
    assert response.status_code == 409 and error_code(response) == "stock_item_inactive"


def test_opening_stock_on_an_unknown_item_is_404(client, manager, data):
    _, headers = manager
    response = opening(client, headers, 99999)
    assert response.status_code == 404 and error_code(response) == "stock_item_not_found"


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "two", None, 1_000_001])
def test_opening_quantity_is_a_whole_number_above_zero(client, manager, cable, quantity):
    _, headers = manager
    response = opening(client, headers, cable, quantity=quantity)
    assert response.status_code == 422 and error_code(response) == "validation_error"
    assert movements(cable) == []


def test_opening_date_cannot_be_in_the_future(client, manager, cable):
    _, headers = manager
    response = opening(client, headers, cable, movement_date=(today() + timedelta(days=1)).isoformat())
    assert response.status_code == 422 and error_code(response) == "movement_date_in_future"


def test_opening_note_up_to_500_characters(client, manager, cable):
    _, headers = manager
    too_long = opening(client, headers, cable, note="n" * 501)
    assert too_long.status_code == 422 and error_code(too_long) == "invalid_reason"
    assert opening(client, headers, cable, note="n" * 500).status_code == 200


@pytest.mark.parametrize("extra", [{"balance_after": 1}, {"reason": "x"}, {"employee_id": 1}])
def test_opening_unknown_fields_are_refused(client, manager, cable, extra):
    _, headers = manager
    response = opening(client, headers, cable, **extra)
    assert response.status_code == 422 and error_code(response) == "validation_error"


def test_opening_failure_saves_nothing(client, manager, cable, monkeypatch):
    _, headers = manager

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(audit_service, "record", broken_record)
    with pytest.raises(RuntimeError):
        opening(client, headers, cable)
    assert on_hand(cable) == 0 and movements(cable) == []


def test_history_shows_the_opening_movement(client, manager, cable):
    _, headers = manager
    opening(client, headers, cable, quantity=12, note="Initial count")
    [row] = client.get(f"{ITEMS}/{cable}/movements", headers=headers).json()["items"]
    assert row["movement_type"] == "opening" and row["reason"] == "Initial count" and row["reference"] is None


# ---- Roles ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_enter_existing_equipment(client, staff_headers, data, cable, role):
    _, headers = staff_headers(role)
    assert enter(client, headers, data).status_code == 201
    assert opening(client, headers, cable).status_code == 200


def test_employee_role_cannot_enter_existing_equipment(client, staff_headers, data, cable):
    _, headers = staff_headers("Employee")
    for response in (enter(client, headers, data), opening(client, headers, cable)):
        assert response.status_code == 403 and error_code(response) == "forbidden"
    assert asset_count() == 0 and movements(cable) == []


def test_login_is_needed(client, data, cable):
    assert client.post(ASSETS, json=laptop(category_id=data["laptops"])).status_code == 401
    assert client.post(f"{ITEMS}/{cable}/opening-stock", json={"quantity": 1}).status_code == 401
