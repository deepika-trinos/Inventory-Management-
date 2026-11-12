"""Bulk stock items API (Slice 2.4, INV-01, PRD 9.2, BR-12, BR-13, decisions B35-B39)."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.modules.audit.models import AuditLog
from app.modules.categories import service as categories_service
from app.modules.categories.models import AssetCategory
from app.modules.inventory import service
from app.modules.inventory.models import StockItem
from tests.conftest import auth_header

ITEMS = "/api/v1/stock-items"
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
def categories(db):
    """Peripherals (bulk), Cables (bulk), Laptops (serialized), Old stock (bulk, inactive)."""
    made = {
        name: categories_service.create_category(db, name=name, tracking_type=kind)
        for name, kind in [("Peripherals", "bulk"), ("Cables", "bulk"), ("Laptops", "serialized"), ("Old stock", "bulk")]
    }
    categories_service.set_active(db, actor=None, category=made["Old stock"], active=False)
    return {name: c.id for name, c in made.items()}


def create(client, headers, category_id, **body):
    body = {"name": "USB mouse", "category_id": category_id, "unit_of_measure": "pieces", "reorder_threshold": 10, **body}
    return client.post(ITEMS, headers=headers, json=body)


def audit_for(item_id: int, action: str | None = None) -> list[AuditLog]:
    with SessionLocal() as fresh:
        stmt = select(AuditLog).where(AuditLog.entity_type == "stock_items", AuditLog.entity_id == str(item_id))
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return list(fresh.scalars(stmt.order_by(AuditLog.id)).all())


def in_database(item_id: int) -> StockItem | None:
    with SessionLocal() as fresh:
        return fresh.get(StockItem, item_id)


# ---- Roles: Admin and IT Manager only -------------------------------------------------
ENDPOINTS = [
    ("get", ITEMS, None),
    ("post", ITEMS, {"name": "X", "category_id": 1, "unit_of_measure": "pieces", "reorder_threshold": 0}),
    ("get", f"{ITEMS}/1", None),
    ("patch", f"{ITEMS}/1", {"name": "Y"}),
    ("post", f"{ITEMS}/1/activate", None),
    ("post", f"{ITEMS}/1/deactivate", None),
]


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_employee_role_gets_403_on_every_stock_item_endpoint(client, staff_headers, method, url, body):
    _, headers = staff_headers("Employee")

    response = client.request(method, url, json=body, headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_stock_item_endpoints_need_login(client, method, url, body):
    assert client.request(method, url, json=body).status_code == 401


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_use_every_endpoint(client, staff_headers, categories, role):
    _, headers = staff_headers(role)

    created = create(client, headers, categories["Peripherals"])
    iid = created.json()["id"]

    assert created.status_code == 201
    assert client.get(ITEMS, headers=headers).status_code == 200
    assert client.get(f"{ITEMS}/{iid}", headers=headers).status_code == 200
    assert client.patch(f"{ITEMS}/{iid}", headers=headers, json={"reorder_threshold": 5}).status_code == 200
    assert client.post(f"{ITEMS}/{iid}/deactivate", headers=headers).status_code == 200
    assert client.post(f"{ITEMS}/{iid}/activate", headers=headers).status_code == 200


# ---- Done-check: a mouse with its threshold ------------------------------------------------
def test_mouse_is_set_up_with_its_threshold(client, manager, categories):
    user, headers = manager

    response = create(client, headers, categories["Peripherals"], name="  USB mouse ", reorder_threshold=10)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "USB mouse"
    assert body["category"] == {"id": categories["Peripherals"], "name": "Peripherals", "tracking_type": "bulk", "status": "active"}
    assert (body["unit_of_measure"], body["reorder_threshold"]) == ("pieces", 10)
    assert body["quantity_on_hand"] == 0 and body["status"] == "active"
    [row] = audit_for(body["id"], "stock_item.created")
    assert row.actor_user_id == user.id and row.before_data is None
    assert row.after_data == {
        "name": "USB mouse", "category_id": categories["Peripherals"], "category": "Peripherals",
        "unit_of_measure": "pieces", "reorder_threshold": 10, "quantity_on_hand": 0, "status": "active",
    }


def test_threshold_zero_is_allowed(client, manager, categories):
    _, headers = manager
    assert create(client, headers, categories["Cables"], name="HDMI cable", reorder_threshold=0).status_code == 201


# ---- Category rules (PRD 9.2) ---------------------------------------------------------------
def test_serialized_category_is_rejected(client, manager, categories):
    _, headers = manager

    response = create(client, headers, categories["Laptops"], name="Laptop")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_not_bulk"
    assert "one by one" in response.json()["error"]["message"]
    assert client.get(ITEMS, headers=headers).json()["total"] == 0


def test_inactive_category_is_rejected(client, manager, categories):
    _, headers = manager

    response = create(client, headers, categories["Old stock"])

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_inactive"


def test_unknown_category_is_404(client, manager, categories):
    _, headers = manager
    response = create(client, headers, 9999)
    assert response.status_code == 404 and response.json()["error"]["code"] == "category_not_found"


def test_moving_to_a_serialized_or_inactive_category_is_rejected(client, manager, categories):
    _, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]

    serialized = client.patch(f"{ITEMS}/{iid}", headers=headers, json={"category_id": categories["Laptops"]})
    inactive = client.patch(f"{ITEMS}/{iid}", headers=headers, json={"category_id": categories["Old stock"]})
    ok = client.patch(f"{ITEMS}/{iid}", headers=headers, json={"category_id": categories["Cables"]})

    assert serialized.json()["error"]["code"] == "category_not_bulk"
    assert inactive.json()["error"]["code"] == "category_inactive"
    assert ok.status_code == 200 and ok.json()["category"]["name"] == "Cables"
    [row] = audit_for(iid, "stock_item.updated")
    assert (row.before_data["category"], row.after_data["category"]) == ("Peripherals", "Cables")


def test_item_keeps_working_when_its_category_is_deactivated_later(client, manager, categories):
    _, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]
    client.post(f"{CATEGORIES}/{categories['Peripherals']}/deactivate", headers=headers)

    edit = client.patch(f"{ITEMS}/{iid}", headers=headers, json={"reorder_threshold": 3})

    assert edit.status_code == 200  # same category: not re-checked
    assert edit.json()["category"]["status"] == "inactive"


def test_category_with_stock_items_cannot_switch_tracking_type(client, manager, categories):
    """The Slice 2.1 guard now counts stock items as "in use"."""
    _, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]
    client.post(f"{ITEMS}/{iid}/deactivate", headers=headers)  # inactive items still count

    response = client.patch(
        f"{CATEGORIES}/{categories['Peripherals']}", headers=headers, json={"tracking_type": "serialized"}
    )
    free = client.patch(f"{CATEGORIES}/{categories['Cables']}", headers=headers, json={"tracking_type": "serialized"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "tracking_type_locked"
    assert free.status_code == 200  # no items: still allowed


# ---- quantity_on_hand is read-only -------------------------------------------------------------
def test_quantity_cannot_be_set_on_create(client, manager, categories):
    _, headers = manager

    response = create(client, headers, categories["Peripherals"], quantity_on_hand=50)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "quantity_on_hand" in str(response.json()["error"]["details"])
    assert client.get(ITEMS, headers=headers).json()["total"] == 0


def test_quantity_cannot_be_set_on_edit(client, manager, categories):
    _, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]

    response = client.patch(f"{ITEMS}/{iid}", headers=headers, json={"quantity_on_hand": 50})

    assert response.status_code == 422
    assert in_database(iid).quantity_on_hand == 0


def test_database_rejects_negative_quantity_and_threshold(db, categories):
    for bad in (
        StockItem(name="A", category_id=categories["Cables"], unit_of_measure="pieces", reorder_threshold=0, quantity_on_hand=-1),
        StockItem(name="B", category_id=categories["Cables"], unit_of_measure="pieces", reorder_threshold=-1),
        StockItem(name="C", category_id=categories["Cables"], unit_of_measure="dozens", reorder_threshold=0),
    ):
        db.add(bad)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


# ---- Validation ---------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"reorder_threshold": -1}, "validation_error"),
        ({"reorder_threshold": None}, "validation_error"),
        ({"reorder_threshold": 1.5}, "validation_error"),
        ({"unit_of_measure": "dozens"}, "validation_error"),
        ({"unit_of_measure": None}, "validation_error"),
        ({"name": ""}, "validation_error"),
        ({"name": "   "}, "invalid_name"),
        ({"name": "x" * 151}, "validation_error"),
    ],
)
def test_create_validation(client, manager, categories, changes, code):
    _, headers = manager
    body = {"name": "USB mouse", "category_id": categories["Peripherals"], "unit_of_measure": "pieces",
            "reorder_threshold": 10, **changes}
    body = {k: v for k, v in body.items() if v is not None}

    response = client.post(ITEMS, headers=headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize("unit", ["pieces", "boxes", "packs", "pairs", "sets", "rolls", "metres"])
def test_every_listed_unit_is_accepted(client, manager, categories, unit):
    _, headers = manager
    assert create(client, headers, categories["Cables"], name=f"Item in {unit}", unit_of_measure=unit).status_code == 201


def test_edit_validation(client, manager, categories):
    _, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]

    negative = client.patch(f"{ITEMS}/{iid}", headers=headers, json={"reorder_threshold": -5})
    blank = client.patch(f"{ITEMS}/{iid}", headers=headers, json={"name": "  "})

    assert negative.status_code == 422
    assert blank.status_code == 422 and blank.json()["error"]["code"] == "invalid_name"
    assert in_database(iid).reorder_threshold == 10


# ---- Names: unique within a category ------------------------------------------------------------
@pytest.mark.parametrize("name", ["USB mouse", "usb MOUSE", "  Usb Mouse "])
def test_duplicate_name_in_the_same_category_is_blocked(client, manager, categories, name):
    _, headers = manager
    assert create(client, headers, categories["Peripherals"]).status_code == 201

    response = create(client, headers, categories["Peripherals"], name=name)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stock_item_name_taken"


def test_same_name_in_another_category_is_allowed(client, manager, categories):
    _, headers = manager
    create(client, headers, categories["Peripherals"], name="Adapter")

    assert create(client, headers, categories["Cables"], name="adapter").status_code == 201


def test_moving_into_a_category_with_the_same_name_is_blocked(client, manager, categories):
    _, headers = manager
    create(client, headers, categories["Cables"], name="Adapter")
    iid = create(client, headers, categories["Peripherals"], name="ADAPTER").json()["id"]

    response = client.patch(f"{ITEMS}/{iid}", headers=headers, json={"category_id": categories["Cables"]})

    assert response.status_code == 409
    assert in_database(iid).category_id == categories["Peripherals"]


def test_database_index_blocks_duplicates_even_without_the_service(db, categories):
    db.add(StockItem(name="Dock", category_id=categories["Cables"], unit_of_measure="pieces", reorder_threshold=0))
    db.commit()
    db.add(StockItem(name="DOCK", category_id=categories["Cables"], unit_of_measure="pieces", reorder_threshold=0))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---- Read: search, filters, sorting --------------------------------------------------------------
def test_list_search_filters_and_sort(client, manager, categories):
    _, headers = manager
    for name, cat, threshold in [("USB mouse", "Peripherals", 10), ("Keyboard", "Peripherals", 5),
                                 ("HDMI cable", "Cables", 20), ("USB-C cable", "Cables", 8)]:
        create(client, headers, categories[cat], name=name, reorder_threshold=threshold)
    kb = client.get(ITEMS, headers=headers, params={"search": "keyboard"}).json()["items"][0]["id"]
    client.post(f"{ITEMS}/{kb}/deactivate", headers=headers)

    def names(**params):
        return [i["name"] for i in client.get(ITEMS, headers=headers, params=params).json()["items"]]

    assert names() == ["HDMI cable", "Keyboard", "USB mouse", "USB-C cable"]
    assert names(search="usb") == ["USB mouse", "USB-C cable"]
    assert names(category_id=categories["Cables"]) == ["HDMI cable", "USB-C cable"]
    assert names(status="inactive") == ["Keyboard"]
    assert names(sort="-reorder_threshold") == ["HDMI cable", "USB mouse", "USB-C cable", "Keyboard"]
    assert names(sort="category", status="active") == ["HDMI cable", "USB-C cable", "USB mouse"]
    assert names(search="%") == []
    assert client.get(ITEMS, headers=headers, params={"sort": "password"}).status_code == 400


def test_get_one_and_404(client, manager, categories):
    _, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]

    assert client.get(f"{ITEMS}/{iid}", headers=headers).json()["quantity_on_hand"] == 0
    missing = client.get(f"{ITEMS}/9999", headers=headers)
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "stock_item_not_found"


# ---- Edit -------------------------------------------------------------------------------------------
def test_edit_writes_audit_row(client, manager, categories):
    user, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]

    response = client.patch(
        f"{ITEMS}/{iid}", headers=headers, json={"name": "Wireless mouse", "unit_of_measure": "boxes", "reorder_threshold": 4}
    )

    assert response.status_code == 200
    [row] = audit_for(iid, "stock_item.updated")
    assert row.actor_user_id == user.id
    assert (row.before_data["name"], row.after_data["name"]) == ("USB mouse", "Wireless mouse")
    assert (row.before_data["unit_of_measure"], row.after_data["unit_of_measure"]) == ("pieces", "boxes")
    assert (row.before_data["reorder_threshold"], row.after_data["reorder_threshold"]) == (10, 4)


def test_edit_with_no_real_change_writes_no_audit_row(client, manager, categories):
    _, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]

    response = client.patch(
        f"{ITEMS}/{iid}", headers=headers,
        json={"name": " USB mouse ", "reorder_threshold": 10, "category_id": categories["Peripherals"]},
    )

    assert response.status_code == 200
    assert audit_for(iid, "stock_item.updated") == []


def test_unit_locks_once_the_item_has_stock(client, manager, categories, db):
    """No stock movements exist until Slice 3.3, so stock is put in directly here."""
    _, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]
    item = db.get(StockItem, iid)
    item.quantity_on_hand = 5
    db.commit()

    locked = client.patch(f"{ITEMS}/{iid}", headers=headers, json={"unit_of_measure": "boxes"})
    threshold = client.patch(f"{ITEMS}/{iid}", headers=headers, json={"reorder_threshold": 2})

    assert locked.status_code == 409 and locked.json()["error"]["code"] == "unit_locked"
    assert threshold.status_code == 200  # other fields stay editable


# ---- Activate / deactivate, never delete ----------------------------------------------------------
def test_deactivate_and_activate_write_audit_rows(client, manager, categories):
    user, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]

    off = client.post(f"{ITEMS}/{iid}/deactivate", headers=headers)
    client.post(f"{ITEMS}/{iid}/deactivate", headers=headers)  # already inactive: nothing
    on = client.post(f"{ITEMS}/{iid}/activate", headers=headers)

    assert off.json()["status"] == "inactive" and on.json()["status"] == "active"
    assert [r.action for r in audit_for(iid)] == ["stock_item.created", "stock_item.deactivated", "stock_item.activated"]
    [row] = audit_for(iid, "stock_item.deactivated")
    assert row.actor_user_id == user.id
    assert (row.before_data["status"], row.after_data["status"]) == ("active", "inactive")


def test_cannot_deactivate_with_stock_on_hand(client, manager, categories, db):
    _, headers = manager
    iid = create(client, headers, categories["Peripherals"]).json()["id"]
    item = db.get(StockItem, iid)
    item.quantity_on_hand = 3
    db.commit()

    response = client.post(f"{ITEMS}/{iid}/deactivate", headers=headers)

    assert response.status_code == 409 and response.json()["error"]["code"] == "stock_not_zero"
    assert in_database(iid).status == "active"


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_there_is_no_delete(client, staff_headers, categories, role):
    _, headers = staff_headers(role)
    iid = create(client, headers, categories["Peripherals"]).json()["id"]

    response = client.delete(f"{ITEMS}/{iid}", headers=headers)

    assert response.status_code == 405
    assert in_database(iid) is not None
    assert not hasattr(service, "delete_stock_item")


def test_activate_or_deactivate_missing_item_is_404(client, manager):
    _, headers = manager
    assert client.post(f"{ITEMS}/9999/deactivate", headers=headers).status_code == 404
    assert client.post(f"{ITEMS}/9999/activate", headers=headers).status_code == 404


def test_ensure_stock_item_usable(db, categories):
    active = service.create_stock_item(db, name="Mouse", category_id=categories["Cables"], unit_of_measure="pieces", reorder_threshold=1)
    inactive = service.create_stock_item(db, name="Old", category_id=categories["Cables"], unit_of_measure="pieces", reorder_threshold=1)
    service.set_active(db, actor=None, item=inactive, active=False)

    assert service.ensure_stock_item_usable(db, active.id).id == active.id
    with pytest.raises(AppError) as exc:
        service.ensure_stock_item_usable(db, inactive.id)
    assert exc.value.code == "stock_item_inactive"


def test_failed_audit_write_saves_nothing(db, categories, monkeypatch):
    from app.modules.audit import service as audit

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit is down")

    monkeypatch.setattr(audit, "record", broken_record)
    with pytest.raises(RuntimeError):
        service.create_stock_item(db, name="No audit", category_id=categories["Cables"], unit_of_measure="pieces", reorder_threshold=0)

    with SessionLocal() as fresh:
        assert fresh.scalars(select(StockItem)).all() == []
        assert fresh.get(AssetCategory, categories["Cables"]) is not None
