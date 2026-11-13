"""Draft purchases API (Slice 3.1, PUR-01 to PUR-04, PUR-08, BR-06, BR-12, BR-13,
decisions P1-P3, P6, B42-B46)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal, engine
from app.modules.audit.models import AuditLog
from app.modules.categories import service as categories_service
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import StockItem
from app.modules.purchases import service
from app.modules.purchases.models import Purchase, PurchaseLine
from app.modules.purchases.service import _today
from app.modules.vendors import service as vendors_service
from tests.conftest import auth_header

PURCHASES = "/api/v1/purchases"
CATEGORIES = "/api/v1/categories"


@pytest.fixture
def staff_headers(make_user, login):
    def _headers(role: str = "IT Manager"):
        user, password = make_user(role)
        return user, auth_header(login(user.email, password))

    return _headers


@pytest.fixture
def manager(staff_headers):
    return staff_headers("IT Manager")


@pytest.fixture
def data(db):
    """Vendors Acme, Beta (active) and Gone (inactive); categories Laptops (one-by-one),
    Peripherals (by quantity) and Old laptops (one-by-one, inactive); stock items
    USB mouse (active, 25 on hand) and Old mouse (inactive)."""
    acme = vendors_service.create_vendor(db, data={"name": "Acme IT Supplies"})
    beta = vendors_service.create_vendor(db, data={"name": "Beta Traders"})
    gone = vendors_service.create_vendor(db, data={"name": "Gone Ltd"})
    vendors_service.set_active(db, actor=None, vendor=gone, active=False)

    laptops = categories_service.create_category(db, name="Laptops", tracking_type="serialized")
    peripherals = categories_service.create_category(db, name="Peripherals", tracking_type="bulk")
    old_laptops = categories_service.create_category(db, name="Old laptops", tracking_type="serialized")
    categories_service.set_active(db, actor=None, category=old_laptops, active=False)

    mouse = inventory_service.create_stock_item(
        db, name="USB mouse", category_id=peripherals.id, unit_of_measure="pieces", reorder_threshold=5
    )
    old_mouse = inventory_service.create_stock_item(
        db, name="Old mouse", category_id=peripherals.id, unit_of_measure="pieces", reorder_threshold=0
    )
    inventory_service.set_active(db, actor=None, item=old_mouse, active=False)
    # Some stock already on hand, so "unchanged" means more than "still 0" (test-only shortcut).
    mouse.quantity_on_hand = 25
    db.commit()
    return {
        "acme": acme.id, "beta": beta.id, "gone": gone.id,
        "laptops": laptops.id, "peripherals": peripherals.id, "old_laptops": old_laptops.id,
        "mouse": mouse.id, "old_mouse": old_mouse.id,
    }


def laptop_line(category_id, quantity=3, unit_cost="85000.00", description="Laptops: Dell Latitude 5440"):
    return {
        "line_type": "serialized", "category_id": category_id, "description": description,
        "quantity": quantity, "unit_cost": unit_cost,
    }


def mouse_line(stock_item_id, quantity=10, unit_cost="450.00"):
    return {"line_type": "bulk", "stock_item_id": stock_item_id, "quantity": quantity, "unit_cost": unit_cost}


def body_for(data, **overrides):
    body = {
        "vendor_id": data["acme"],
        "reference_number": "INV-2026-0042",
        "purchase_date": _today().isoformat(),
        "notes": "Q4 laptop refresh",
        "lines": [laptop_line(data["laptops"]), mouse_line(data["mouse"])],
    }
    body.update(overrides)
    return body


def create(client, headers, data, **overrides):
    return client.post(PURCHASES, headers=headers, json=body_for(data, **overrides))


def error_code(response):
    return response.json()["error"]["code"]


def audit_for(purchase_id: int, action: str | None = None) -> list[AuditLog]:
    with SessionLocal() as fresh:
        stmt = select(AuditLog).where(AuditLog.entity_type == "purchases", AuditLog.entity_id == str(purchase_id))
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return list(fresh.scalars(stmt.order_by(AuditLog.id)).all())


def stock_on_hand(item_id: int) -> int:
    with SessionLocal() as fresh:
        return fresh.get(StockItem, item_id).quantity_on_hand


def asset_count() -> int:
    """Assets arrive in Slice 3.2. Until then there is no assets table, so a draft
    cannot have made one; once the table exists, this counts its rows."""
    if not inspect(engine).has_table("assets"):
        return 0
    with SessionLocal() as fresh:
        return fresh.execute(text("SELECT count(*) FROM assets")).scalar_one()


def stock_tables_snapshot() -> dict[str, int]:
    """Every stock balance, plus the number of stock movement rows when that table exists (3.3)."""
    with SessionLocal() as fresh:
        result = {f"item:{i.id}": i.quantity_on_hand for i in fresh.scalars(select(StockItem)).all()}
        if inspect(engine).has_table("stock_movements"):
            result["movements"] = fresh.execute(text("SELECT count(*) FROM stock_movements")).scalar_one()
        return result


# ---- Roles: Admin and IT Manager only (P6) -----------------------------------------------
ENDPOINTS = [
    ("get", PURCHASES, None),
    ("post", PURCHASES, {"vendor_id": 1, "reference_number": "X", "purchase_date": "2026-01-01", "lines": []}),
    ("get", f"{PURCHASES}/1", None),
    ("patch", f"{PURCHASES}/1", {"notes": "x"}),
    ("post", f"{PURCHASES}/1/cancel", None),
]


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_employee_role_gets_403_on_every_purchase_endpoint(client, staff_headers, method, url, body):
    _, headers = staff_headers("Employee")

    response = client.request(method, url, json=body, headers=headers)

    assert response.status_code == 403
    assert error_code(response) == "forbidden"


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_purchase_endpoints_need_login(client, method, url, body):
    assert client.request(method, url, json=body).status_code == 401


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_use_every_endpoint(client, staff_headers, data, role):
    _, headers = staff_headers(role)

    created = create(client, headers, data)
    pid = created.json()["id"]

    assert created.status_code == 201
    assert client.get(PURCHASES, headers=headers).status_code == 200
    assert client.get(f"{PURCHASES}/{pid}", headers=headers).status_code == 200
    assert client.patch(f"{PURCHASES}/{pid}", headers=headers, json={"notes": "changed"}).status_code == 200
    assert client.post(f"{PURCHASES}/{pid}/cancel", headers=headers).status_code == 200


# ---- Done-check: a draft with laptops and mice, saved, edited and cancelled; stock unchanged ----
def test_draft_with_laptops_and_mice_is_saved_edited_and_cancelled_without_changing_stock(client, manager, data):
    user, headers = manager
    stock_before = stock_tables_snapshot()
    assert stock_on_hand(data["mouse"]) == 25

    created = create(client, headers, data)

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert body["purchase_number"] == "PUR-000001"
    assert body["vendor"] == {"id": data["acme"], "name": "Acme IT Supplies", "status": "active"}
    assert body["reference_number"] == "INV-2026-0042"
    assert body["received_date"] is None
    assert body["created_by"] == {"id": user.id, "email": user.email}
    laptops, mice = body["lines"]
    assert laptops["line_type"] == "serialized" and laptops["category"]["name"] == "Laptops"
    assert laptops["description"] == "Laptops: Dell Latitude 5440" and laptops["stock_item"] is None
    assert laptops["line_total"] == "255000.00" and laptops["received_quantity"] is None
    assert mice["line_type"] == "bulk" and mice["stock_item"]["name"] == "USB mouse" and mice["category"] is None
    assert mice["unit_cost"] == "450.00" and mice["line_total"] == "4500.00"
    assert body["line_count"] == 2 and body["total_amount"] == "259500.00"
    # Draft: nothing changed in stock and no assets (PUR-08, BR-06).
    assert stock_tables_snapshot() == stock_before and asset_count() == 0

    pid = body["id"]
    edited = client.patch(
        f"{PURCHASES}/{pid}",
        headers=headers,
        json={"lines": [laptop_line(data["laptops"], quantity=5), mouse_line(data["mouse"], quantity=20)]},
    )
    assert edited.status_code == 200, edited.text
    assert [line["quantity"] for line in edited.json()["lines"]] == [5, 20]
    assert edited.json()["total_amount"] == "434000.00"  # 5 x 85000 + 20 x 450
    assert stock_tables_snapshot() == stock_before and asset_count() == 0

    cancelled = client.post(f"{PURCHASES}/{pid}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert len(cancelled.json()["lines"]) == 2  # nothing deleted
    assert stock_tables_snapshot() == stock_before and asset_count() == 0
    assert stock_on_hand(data["mouse"]) == 25


def test_purchase_numbers_are_given_in_order(client, manager, data):
    _, headers = manager
    first = create(client, headers, data, reference_number="A-1").json()
    second = create(client, headers, data, reference_number="A-2").json()
    assert (first["purchase_number"], second["purchase_number"]) == ("PUR-000001", "PUR-000002")


def test_purchase_number_cannot_be_sent(client, manager, data):
    _, headers = manager
    response = create(client, headers, data, purchase_number="PUR-999999")
    assert response.status_code == 422


# ---- Totals are calculated by the server (P2) -----------------------------------------------
def test_totals_are_calculated_without_rounding_errors(client, manager, data):
    _, headers = manager
    response = create(
        client, headers, data,
        lines=[mouse_line(data["mouse"], quantity=3, unit_cost="0.10"), laptop_line(data["laptops"], 1, 1234.5)],
    )
    assert response.status_code == 201, response.text
    lines = response.json()["lines"]
    assert lines[0]["line_total"] == "0.30"
    assert lines[1]["unit_cost"] == "1234.50"
    assert response.json()["total_amount"] == "1234.80"


@pytest.mark.parametrize("field", ["line_total", "total_amount"])
def test_totals_cannot_be_typed_in(client, manager, data, field):
    _, headers = manager
    line = {**mouse_line(data["mouse"]), "line_total": "1.00"} if field == "line_total" else mouse_line(data["mouse"])
    extra = {"total_amount": "1.00"} if field == "total_amount" else {}
    response = create(client, headers, data, lines=[line], **extra)
    assert response.status_code == 422 and error_code(response) == "validation_error"


def test_cost_zero_is_allowed(client, manager, data):
    _, headers = manager
    response = create(client, headers, data, lines=[mouse_line(data["mouse"], unit_cost="0")])
    assert response.status_code == 201
    assert response.json()["total_amount"] == "0.00"


@pytest.mark.parametrize(
    "line_changes",
    [
        {"quantity": 0},
        {"quantity": -1},
        {"quantity": 1.5},
        {"quantity": 100_001},
        {"unit_cost": "-0.01"},
        {"unit_cost": "12.345"},
        {"unit_cost": "10000000000.00"},  # more than NUMERIC(12,2) holds
        {"unit_cost": "abc"},
    ],
)
def test_bad_quantity_or_cost_is_rejected(client, manager, data, line_changes):
    _, headers = manager
    response = create(client, headers, data, lines=[{**mouse_line(data["mouse"]), **line_changes}])
    assert response.status_code == 422 and error_code(response) == "validation_error"
    with SessionLocal() as fresh:
        assert fresh.scalars(select(Purchase)).all() == []


# ---- Vendor, items and categories must be usable --------------------------------------------
def test_inactive_vendor_is_rejected(client, manager, data):
    _, headers = manager
    response = create(client, headers, data, vendor_id=data["gone"])
    assert response.status_code == 409 and error_code(response) == "vendor_inactive"


def test_unknown_vendor_is_404(client, manager, data):
    _, headers = manager
    response = create(client, headers, data, vendor_id=9999)
    assert response.status_code == 404 and error_code(response) == "vendor_not_found"


def test_inactive_stock_item_is_rejected_with_its_line_number(client, manager, data):
    _, headers = manager
    response = create(client, headers, data, lines=[laptop_line(data["laptops"]), mouse_line(data["old_mouse"])])
    assert response.status_code == 409 and error_code(response) == "stock_item_inactive"
    assert response.json()["error"]["details"] == {"line": 2}
    assert response.json()["error"]["message"].startswith("Line 2:")


def test_inactive_category_is_rejected(client, manager, data):
    _, headers = manager
    response = create(client, headers, data, lines=[laptop_line(data["old_laptops"])])
    assert response.status_code == 409 and error_code(response) == "category_inactive"
    assert response.json()["error"]["details"] == {"line": 1}


def test_bulk_category_on_a_serialized_line_is_rejected(client, manager, data):
    _, headers = manager
    response = create(client, headers, data, lines=[laptop_line(data["peripherals"])])
    assert response.status_code == 409 and error_code(response) == "category_not_serialized"


@pytest.mark.parametrize("category_key", ["laptops", "peripherals"])
def test_category_on_a_bulk_line_is_rejected(client, manager, data, category_key):
    """A by-quantity line points to a stock item only (P1), never to a category."""
    _, headers = manager
    line = {**mouse_line(data["mouse"]), "category_id": data[category_key]}
    response = create(client, headers, data, lines=[line])
    assert response.status_code == 422 and error_code(response) == "invalid_line"


@pytest.mark.parametrize(
    "line",
    [
        {"line_type": "bulk", "quantity": 1, "unit_cost": "1"},  # no stock item
        {"line_type": "bulk", "stock_item_id": "MOUSE", "description": "x", "quantity": 1, "unit_cost": "1"},
        {"line_type": "serialized", "quantity": 1, "unit_cost": "1", "description": "x"},  # no category
        {"line_type": "serialized", "category_id": "LAPTOPS", "quantity": 1, "unit_cost": "1"},  # no description
        {"line_type": "serialized", "category_id": "LAPTOPS", "description": "   ", "quantity": 1, "unit_cost": "1"},
        {"line_type": "serialized", "category_id": "LAPTOPS", "stock_item_id": "MOUSE", "description": "x",
         "quantity": 1, "unit_cost": "1"},
    ],
)
def test_incomplete_or_mixed_lines_are_rejected(client, manager, data, line):
    _, headers = manager
    line = {k: data["mouse"] if v == "MOUSE" else data["laptops"] if v == "LAPTOPS" else v for k, v in line.items()}
    response = create(client, headers, data, lines=[line])
    assert response.status_code == 422 and error_code(response) == "invalid_line"


def test_unknown_line_type_is_rejected(client, manager, data):
    _, headers = manager
    response = create(client, headers, data, lines=[{**mouse_line(data["mouse"]), "line_type": "asset"}])
    assert response.status_code == 422 and error_code(response) == "validation_error"


def test_unknown_stock_item_or_category_is_404(client, manager, data):
    _, headers = manager
    assert error_code(create(client, headers, data, lines=[mouse_line(9999)])) == "stock_item_not_found"
    assert error_code(create(client, headers, data, lines=[laptop_line(9999)])) == "category_not_found"


def test_at_least_one_line_is_needed(client, manager, data):
    _, headers = manager
    response = create(client, headers, data, lines=[])
    assert response.status_code == 422 and error_code(response) == "lines_required"


def test_serialized_lines_only_or_bulk_lines_only_are_fine(client, manager, data):
    _, headers = manager
    assert create(client, headers, data, reference_number="R1", lines=[laptop_line(data["laptops"])]).status_code == 201
    assert create(client, headers, data, reference_number="R2", lines=[mouse_line(data["mouse"])]).status_code == 201


# ---- Reference number and date (P3) -------------------------------------------------------------
@pytest.mark.parametrize("reference", ["inv-2026-0042", "INV-2026-0042", "  Inv-2026-0042  "])
def test_duplicate_reference_for_the_same_vendor_is_blocked_in_any_case(client, manager, data, reference):
    _, headers = manager
    assert create(client, headers, data).status_code == 201

    response = create(client, headers, data, reference_number=reference)

    assert response.status_code == 409 and error_code(response) == "purchase_reference_taken"


def test_same_reference_for_another_vendor_is_allowed(client, manager, data):
    _, headers = manager
    assert create(client, headers, data).status_code == 201
    assert create(client, headers, data, vendor_id=data["beta"]).status_code == 201


def test_cancelled_purchase_frees_its_reference(client, manager, data):
    _, headers = manager
    pid = create(client, headers, data).json()["id"]
    client.post(f"{PURCHASES}/{pid}/cancel", headers=headers)

    response = create(client, headers, data, reference_number="inv-2026-0042")

    assert response.status_code == 201


def test_database_index_blocks_duplicate_references_even_without_the_service(db, data, make_user):
    user, _ = make_user("IT Manager")
    db.add(Purchase(vendor_id=data["acme"], reference_number="X-1", purchase_date=date(2026, 1, 1), created_by_user_id=user.id))
    db.commit()
    db.add(Purchase(vendor_id=data["acme"], reference_number="x-1", purchase_date=date(2026, 1, 1), created_by_user_id=user.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_reference_is_trimmed_and_blank_is_rejected(client, manager, data):
    _, headers = manager
    assert create(client, headers, data, reference_number="  INV-7  ").json()["reference_number"] == "INV-7"
    response = create(client, headers, data, reference_number="   ")
    assert response.status_code == 422 and error_code(response) == "invalid_reference"


def test_missing_reference_or_date_is_rejected(client, manager, data):
    _, headers = manager
    for field in ("reference_number", "purchase_date", "vendor_id"):
        body = body_for(data)
        del body[field]
        response = client.post(PURCHASES, headers=headers, json=body)
        assert response.status_code == 422 and error_code(response) == "validation_error"


def test_future_date_is_rejected_but_today_and_past_are_fine(client, manager, data):
    _, headers = manager
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    response = create(client, headers, data, purchase_date=tomorrow)
    assert response.status_code == 422 and error_code(response) == "purchase_date_in_future"

    assert create(client, headers, data, reference_number="T", purchase_date=_today().isoformat()).status_code == 201
    assert create(client, headers, data, reference_number="P", purchase_date="2025-03-31").status_code == 201


# ---- Editing a draft --------------------------------------------------------------------------
def test_edit_writes_audit_row_with_before_and_after(client, manager, data):
    user, headers = manager
    pid = create(client, headers, data).json()["id"]

    response = client.patch(
        f"{PURCHASES}/{pid}",
        headers=headers,
        json={"vendor_id": data["beta"], "reference_number": "B-77", "purchase_date": "2026-01-15", "notes": None},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["vendor"]["name"] == "Beta Traders" and body["reference_number"] == "B-77"
    assert body["purchase_date"] == "2026-01-15" and body["notes"] is None
    [row] = audit_for(pid, "purchase.updated")
    assert row.actor_user_id == user.id
    assert row.before_data["vendor"] == "Acme IT Supplies" and row.after_data["vendor"] == "Beta Traders"
    assert row.before_data["notes"] == "Q4 laptop refresh" and row.after_data["notes"] is None
    assert row.after_data["total_amount"] == "259500.00"


def test_edit_with_no_real_change_writes_no_audit_row(client, manager, data):
    _, headers = manager
    created = create(client, headers, data).json()
    same = body_for(data)

    response = client.patch(f"{PURCHASES}/{created['id']}", headers=headers, json=same)

    assert response.status_code == 200
    assert audit_for(created["id"], "purchase.updated") == []
    assert [line["id"] for line in response.json()["lines"]] == [line["id"] for line in created["lines"]]


def test_edit_lines_replace_all_lines(client, manager, data):
    _, headers = manager
    pid = create(client, headers, data).json()["id"]

    response = client.patch(f"{PURCHASES}/{pid}", headers=headers, json={"lines": [mouse_line(data["mouse"], 2)]})

    assert response.status_code == 200
    assert [(line["line_type"], line["quantity"]) for line in response.json()["lines"]] == [("bulk", 2)]
    with SessionLocal() as fresh:
        assert len(fresh.scalars(select(PurchaseLine)).all()) == 1


def test_edit_validates_like_create(client, manager, data):
    _, headers = manager
    pid = create(client, headers, data).json()["id"]
    url = f"{PURCHASES}/{pid}"
    tomorrow = (_today() + timedelta(days=1)).isoformat()

    assert error_code(client.patch(url, headers=headers, json={"vendor_id": data["gone"]})) == "vendor_inactive"
    assert error_code(client.patch(url, headers=headers, json={"lines": []})) == "lines_required"
    assert error_code(client.patch(url, headers=headers, json={"purchase_date": tomorrow})) == "purchase_date_in_future"
    assert error_code(client.patch(url, headers=headers, json={"reference_number": " "})) == "invalid_reference"
    assert error_code(client.patch(url, headers=headers, json={"lines": [mouse_line(data["old_mouse"])]})) == "stock_item_inactive"
    assert error_code(client.patch(url, headers=headers, json={"lines": [laptop_line(data["old_laptops"])]})) == "category_inactive"
    assert client.patch(url, headers=headers, json={"lines": [{**mouse_line(data["mouse"]), "quantity": 0}]}).status_code == 422
    assert audit_for(pid, "purchase.updated") == []


def test_edit_into_a_duplicate_reference_is_blocked(client, manager, data):
    _, headers = manager
    create(client, headers, data, reference_number="A-1")
    create(client, headers, data, vendor_id=data["beta"], reference_number="B-1")
    pid = create(client, headers, data, reference_number="A-2").json()["id"]
    url = f"{PURCHASES}/{pid}"

    assert error_code(client.patch(url, headers=headers, json={"reference_number": "a-1"})) == "purchase_reference_taken"
    moved = client.patch(url, headers=headers, json={"vendor_id": data["beta"], "reference_number": "b-1"})
    assert error_code(moved) == "purchase_reference_taken"
    # Changing only the case of its own number is fine.
    assert client.patch(url, headers=headers, json={"reference_number": "a-2"}).status_code == 200


def test_edit_checks_only_what_changed(client, manager, data, db):
    """B45: things deactivated after the draft was saved do not block an edit
    that leaves them as they are; adding them anew is blocked."""
    _, headers = manager
    pid = create(client, headers, data).json()["id"]
    vendors_service.set_active(db, actor=None, vendor=vendors_service.get_vendor(db, data["acme"]), active=False)
    mouse = inventory_service.get_stock_item(db, data["mouse"])
    mouse.quantity_on_hand = 0  # B38: only an item with no stock can be deactivated
    db.commit()
    inventory_service.set_active(db, actor=None, item=mouse, active=False)
    url = f"{PURCHASES}/{pid}"

    kept = client.patch(
        url,
        headers=headers,
        json={"notes": "still fine", "lines": [laptop_line(data["laptops"], 4), mouse_line(data["mouse"], 12)]},
    )
    assert kept.status_code == 200, kept.text
    assert kept.json()["total_amount"] == "345400.00"  # 4 x 85000 + 12 x 450

    other = create(client, headers, data, vendor_id=data["beta"], reference_number="NEW", lines=[laptop_line(data["laptops"])])
    added = client.patch(
        f"{PURCHASES}/{other.json()['id']}",
        headers=headers,
        json={"lines": [laptop_line(data["laptops"]), mouse_line(data["mouse"])]},
    )
    assert added.status_code == 409 and error_code(added) == "stock_item_inactive"


def test_edit_unknown_purchase_is_404(client, manager):
    _, headers = manager
    assert client.patch(f"{PURCHASES}/9999", headers=headers, json={"notes": "x"}).status_code == 404
    assert client.post(f"{PURCHASES}/9999/cancel", headers=headers).status_code == 404


# ---- Cancelling (only drafts; final) ----------------------------------------------------------
def test_cancel_writes_audit_row(client, manager, data):
    user, headers = manager
    pid = create(client, headers, data).json()["id"]

    client.post(f"{PURCHASES}/{pid}/cancel", headers=headers)

    [row] = audit_for(pid, "purchase.cancelled")
    assert row.actor_user_id == user.id
    assert row.before_data["status"] == "draft" and row.after_data["status"] == "cancelled"
    assert len(row.after_data["lines"]) == 2


def test_cancelled_purchase_cannot_be_edited_or_cancelled_again(client, manager, data):
    _, headers = manager
    pid = create(client, headers, data).json()["id"]
    client.post(f"{PURCHASES}/{pid}/cancel", headers=headers)

    edit = client.patch(f"{PURCHASES}/{pid}", headers=headers, json={"notes": "too late"})
    again = client.post(f"{PURCHASES}/{pid}/cancel", headers=headers)

    assert edit.status_code == 409 and error_code(edit) == "purchase_not_draft"
    assert again.status_code == 409 and error_code(again) == "purchase_not_draft"
    assert len(audit_for(pid, "purchase.cancelled")) == 1
    assert audit_for(pid, "purchase.updated") == []


def test_received_purchase_cannot_be_edited_or_cancelled(client, manager, data, db):
    _, headers = manager
    pid = create(client, headers, data).json()["id"]
    # Receiving arrives in Slices 3.2 / 3.3; set the status directly to prove the rule now.
    purchase = db.get(Purchase, pid)
    purchase.status, purchase.received_date = "received", _today()
    db.commit()

    assert error_code(client.patch(f"{PURCHASES}/{pid}", headers=headers, json={"notes": "x"})) == "purchase_not_draft"
    assert error_code(client.post(f"{PURCHASES}/{pid}/cancel", headers=headers)) == "purchase_not_draft"


def test_draft_can_be_cancelled_after_its_vendor_was_deactivated(client, manager, data, db):
    _, headers = manager
    pid = create(client, headers, data).json()["id"]
    vendors_service.set_active(db, actor=None, vendor=vendors_service.get_vendor(db, data["acme"]), active=False)

    assert client.post(f"{PURCHASES}/{pid}/cancel", headers=headers).status_code == 200


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_there_is_no_delete(client, staff_headers, data, role):
    _, headers = staff_headers(role)
    pid = create(client, headers, data).json()["id"]

    response = client.delete(f"{PURCHASES}/{pid}", headers=headers)

    assert response.status_code == 405
    assert client.get(f"{PURCHASES}/{pid}", headers=headers).json()["status"] == "draft"
    assert not hasattr(service, "delete_purchase")


# ---- Audit on create (BR-13) --------------------------------------------------------------------
def test_create_writes_audit_row(client, manager, data):
    user, headers = manager
    pid = create(client, headers, data).json()["id"]

    [row] = audit_for(pid)
    assert row.action == "purchase.created" and row.actor_user_id == user.id and row.before_data is None
    after = row.after_data
    assert after["purchase_number"] == "PUR-000001" and after["status"] == "draft"
    assert after["vendor"] == "Acme IT Supplies" and after["total_amount"] == "259500.00"
    assert [line["line_type"] for line in after["lines"]] == ["serialized", "bulk"]
    assert after["lines"][1]["stock_item"] == "USB mouse" and after["lines"][1]["line_total"] == "4500.00"


def test_failed_audit_write_saves_nothing(db, data, make_user, monkeypatch):
    from app.modules.audit import service as audit

    user, _ = make_user("IT Manager")

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit is down")

    monkeypatch.setattr(audit, "record", broken_record)
    with pytest.raises(RuntimeError):
        service.create_purchase(
            db,
            data={"vendor_id": data["acme"], "reference_number": "R", "purchase_date": _today(),
                  "lines": [mouse_line(data["mouse"])]},
            actor=user,
        )

    with SessionLocal() as fresh:
        assert fresh.scalars(select(Purchase)).all() == []
        assert fresh.scalars(select(PurchaseLine)).all() == []


# ---- Reading: list, search, filters, get one ---------------------------------------------------
def test_list_search_filters_sort_and_paging(client, manager, data):
    _, headers = manager
    a1 = create(client, headers, data, reference_number="INV-100").json()
    create(client, headers, data, reference_number="INV-200", purchase_date="2026-01-01")
    b1 = create(client, headers, data, vendor_id=data["beta"], reference_number="BT-9").json()
    client.post(f"{PURCHASES}/{a1['id']}/cancel", headers=headers)

    def refs(**params):
        response = client.get(PURCHASES, headers=headers, params=params)
        assert response.status_code == 200, response.text
        return [p["reference_number"] for p in response.json()["items"]]

    assert refs() == ["BT-9", "INV-200", "INV-100"]  # newest first
    assert refs(search="inv-1") == ["INV-100"]
    assert refs(search="BETA") == ["BT-9"]
    assert refs(search="pur-000003") == ["BT-9"]
    assert refs(status="cancelled") == ["INV-100"]
    assert refs(status="draft", vendor_id=data["acme"]) == ["INV-200"]
    assert refs(vendor_id=data["beta"]) == ["BT-9"]
    assert refs(sort="purchase_date")[0] == "INV-200"
    assert refs(sort="-vendor")[0] == "BT-9"
    page = client.get(PURCHASES, headers=headers, params={"page": 2, "page_size": 2}).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    listed = client.get(PURCHASES, headers=headers, params={"search": "BT-9"}).json()["items"][0]
    assert listed["id"] == b1["id"] and listed["total_amount"] == "259500.00" and listed["line_count"] == 2
    assert "lines" not in listed
    bad = client.get(PURCHASES, headers=headers, params={"sort": "total_amount"})
    assert bad.status_code == 400 and error_code(bad) == "invalid_sort"
    assert client.get(PURCHASES, headers=headers, params={"status": "open"}).status_code == 422


def test_get_one_and_404(client, manager, data):
    _, headers = manager
    pid = create(client, headers, data).json()["id"]
    assert client.get(f"{PURCHASES}/{pid}", headers=headers).json()["notes"] == "Q4 laptop refresh"
    missing = client.get(f"{PURCHASES}/9999", headers=headers)
    assert missing.status_code == 404 and error_code(missing) == "purchase_not_found"


# ---- Category tracking type locks once a purchase line uses it (B14, B46) ------------------------
def test_category_on_a_purchase_line_cannot_switch_tracking_type(client, manager, data):
    _, headers = manager
    pid = create(client, headers, data, lines=[laptop_line(data["laptops"])]).json()["id"]
    client.post(f"{PURCHASES}/{pid}/cancel", headers=headers)  # any status still counts

    response = client.patch(f"{CATEGORIES}/{data['laptops']}", headers=headers, json={"tracking_type": "bulk"})

    assert response.status_code == 409 and error_code(response) == "tracking_type_locked"


# ---- Database safety nets -------------------------------------------------------------------------
@pytest.mark.parametrize(
    "line",
    [
        {"line_type": "bulk", "stock_item_id": "MOUSE", "category_id": "LAPTOPS", "quantity": 1, "unit_cost": 1},
        {"line_type": "bulk", "quantity": 1, "unit_cost": 1},
        {"line_type": "serialized", "stock_item_id": "MOUSE", "description": "x", "quantity": 1, "unit_cost": 1},
        {"line_type": "serialized", "category_id": "LAPTOPS", "quantity": 1, "unit_cost": 1},
        {"line_type": "bulk", "stock_item_id": "MOUSE", "quantity": 0, "unit_cost": 1},
        {"line_type": "bulk", "stock_item_id": "MOUSE", "quantity": 1, "unit_cost": Decimal("-1")},
        {"line_type": "bulk", "stock_item_id": "MOUSE", "quantity": 2, "unit_cost": 1, "received_quantity": 3},
        {"line_type": "other", "stock_item_id": "MOUSE", "quantity": 1, "unit_cost": 1},
    ],
)
def test_database_rejects_invalid_lines(db, data, make_user, line):
    user, _ = make_user("IT Manager")
    purchase = Purchase(vendor_id=data["acme"], reference_number="DB", purchase_date=date(2026, 1, 1), created_by_user_id=user.id)
    db.add(purchase)
    db.commit()
    line = {k: data["mouse"] if v == "MOUSE" else data["laptops"] if v == "LAPTOPS" else v for k, v in line.items()}
    db.add(PurchaseLine(purchase_id=purchase.id, **line))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_database_rejects_received_date_on_a_draft_and_unknown_status(db, data, make_user):
    user, _ = make_user("IT Manager")
    for extra in ({"received_date": date(2026, 1, 2)}, {"status": "open"}):
        db.add(Purchase(vendor_id=data["acme"], reference_number="DB", purchase_date=date(2026, 1, 1),
                        created_by_user_id=user.id, **extra))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
