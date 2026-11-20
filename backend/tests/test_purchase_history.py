"""Purchase history (Slice 3.4: PUR-09, VEN-04; decisions D1-D4).

Reading only: the purchase list with search and filters (date range too), the
purchase detail with the assets and stock movements a receipt created, and a
vendor's purchase history (the list endpoint with vendor_id)."""

from datetime import timedelta

import pytest

from app.core.database import SessionLocal
from app.modules.purchases.models import Purchase
from app.modules.purchases.service import _today
from app.modules.vendors import service as vendors_service
from tests.test_purchases_api import (  # noqa: F401  (pytest fixtures used by name)
    PURCHASES,
    create,
    data,
    error_code,
    laptop_line,
    manager,
    mouse_line,
    staff_headers,
)
from tests.test_receive_bulk import bulk_receipt
from tests.test_receive_serialized import receive, unit

TODAY = _today()


def draft(client, headers, data, lines=None, **overrides):
    lines = lines or [laptop_line(data["laptops"], quantity=2), mouse_line(data["mouse"], quantity=10)]
    response = create(client, headers, data, lines=lines, **overrides)
    assert response.status_code == 201, response.text
    return response.json()


def received(client, headers, data, **overrides):
    """A received mixed purchase: 2 laptops (2 assets) and 10 mice (1 movement)."""
    purchase = draft(client, headers, data, **overrides)
    body = bulk_receipt(purchase, 2, 10, units={0: [unit(f"SN-{purchase['id']}-1"), unit(f"SN-{purchase['id']}-2")]})
    response = receive(client, headers, purchase, body)
    assert response.status_code == 200, response.text
    return response.json()


def listed(client, headers, **params):
    response = client.get(PURCHASES, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def refs(client, headers, **params):
    return [p["reference_number"] for p in listed(client, headers, **params)["items"]]


# ---- Done-check: a received purchase is visible from the purchase list and the vendor page ----
def test_received_purchase_is_visible_from_the_list_and_the_vendor_page_with_matching_totals(client, manager, data):
    _, headers = manager
    purchase = received(client, headers, data)

    in_list = [p for p in listed(client, headers)["items"] if p["id"] == purchase["id"]]
    on_vendor_page = listed(client, headers, vendor_id=data["acme"], sort="-purchase_date")["items"]
    detail = client.get(f"{PURCHASES}/{purchase['id']}", headers=headers).json()

    assert len(in_list) == 1 and [p["id"] for p in on_vendor_page] == [purchase["id"]]
    for row in (in_list[0], on_vendor_page[0]):
        assert row["status"] == "received"
        assert row["reference_number"] == "INV-2026-0042"
        assert row["vendor"]["name"] == "Acme IT Supplies"
        assert row["purchase_date"] == TODAY.isoformat() and row["received_date"] == TODAY.isoformat()
        assert row["line_count"] == 2
        assert row["total_amount"] == detail["total_amount"] == "174500.00"  # 2 x 85000 + 10 x 450


# ---- Detail (PUR-09) ------------------------------------------------------------------------------
def test_detail_shows_vendor_lines_assets_movements_and_who_did_what(client, manager, data):
    user, headers = manager
    purchase = received(client, headers, data)

    response = client.get(f"{PURCHASES}/{purchase['id']}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["vendor"]["name"] == "Acme IT Supplies"
    assert {"contact_person", "email", "phone", "address"} <= body["vendor"].keys()
    assert body["created_by"] == {"id": user.id, "email": user.email} and body["created_at"]
    assert body["received_by"] == {"id": user.id, "email": user.email}
    assert body["received_at"] and body["received_date"] == TODAY.isoformat()

    laptops, mice = body["lines"]
    assert laptops["category"]["name"] == "Laptops" and laptops["description"] == "Laptops: Dell Latitude 5440"
    assert (laptops["quantity"], laptops["received_quantity"]) == (2, 2)
    assert laptops["unit_cost"] == "85000.00" and laptops["line_total"] == "170000.00"
    assert [(a["asset_code"], a["serial_number"]) for a in laptops["assets"]] == [
        ("AST-000001", f"SN-{purchase['id']}-1"),
        ("AST-000002", f"SN-{purchase['id']}-2"),
    ]
    assert laptops["stock_movements"] == []

    assert mice["stock_item"]["name"] == "USB mouse" and mice["stock_item"]["unit_of_measure"] == "pieces"
    assert (mice["quantity"], mice["received_quantity"]) == (10, 10)
    assert mice["assets"] == []
    [movement] = mice["stock_movements"]
    assert movement["movement_type"] == "receipt" and movement["quantity"] == 10
    assert movement["balance_after"] == 35  # 25 on hand + 10
    assert movement["movement_date"] == TODAY.isoformat() and movement["created_at"]
    assert movement["created_by"] == {"id": user.id, "email": user.email}


def test_receive_response_already_lists_the_movements_and_who_received(client, manager, data):
    user, headers = manager
    purchase = received(client, headers, data)
    assert purchase["received_by"]["id"] == user.id and purchase["received_at"]
    assert [m["quantity"] for m in purchase["lines"][1]["stock_movements"]] == [10]


def test_received_by_and_at_are_stored(client, manager, data):
    user, headers = manager
    purchase = received(client, headers, data)
    with SessionLocal() as fresh:
        saved = fresh.get(Purchase, purchase["id"])
        assert saved.received_by_user_id == user.id and saved.received_at is not None


def test_cancelled_purchase_shows_no_assets_movements_or_receiver(client, manager, data):
    _, headers = manager
    purchase = draft(client, headers, data)
    client.post(f"{PURCHASES}/{purchase['id']}/cancel", headers=headers)

    body = client.get(f"{PURCHASES}/{purchase['id']}", headers=headers).json()

    assert body["status"] == "cancelled"
    assert body["received_by"] is None and body["received_at"] is None and body["received_date"] is None
    assert all(line["assets"] == [] and line["stock_movements"] == [] for line in body["lines"])
    assert all(line["received_quantity"] is None for line in body["lines"])


def test_draft_shows_no_assets_or_movements(client, manager, data):
    _, headers = manager
    purchase = draft(client, headers, data)
    body = client.get(f"{PURCHASES}/{purchase['id']}", headers=headers).json()
    assert body["received_by"] is None
    assert all(line["assets"] == [] and line["stock_movements"] == [] for line in body["lines"])


def test_unknown_purchase_is_404(client, manager):
    _, headers = manager
    response = client.get(f"{PURCHASES}/9999", headers=headers)
    assert response.status_code == 404 and error_code(response) == "purchase_not_found"


# ---- Vendor purchase history (VEN-04) --------------------------------------------------------------
def test_vendor_history_is_newest_purchase_date_first_with_ties_by_number(client, manager, data):
    _, headers = manager
    draft(client, headers, data, reference_number="OLD", purchase_date=(TODAY - timedelta(days=30)).isoformat())
    draft(client, headers, data, reference_number="TODAY-1")
    draft(client, headers, data, reference_number="TODAY-2")
    draft(client, headers, data, reference_number="MID", purchase_date=(TODAY - timedelta(days=3)).isoformat())
    draft(client, headers, data, vendor_id=data["beta"], reference_number="OTHER")

    assert refs(client, headers, vendor_id=data["acme"], sort="-purchase_date") == ["TODAY-2", "TODAY-1", "MID", "OLD"]
    page = listed(client, headers, vendor_id=data["acme"], sort="-purchase_date", page=2, page_size=3)
    assert page["total"] == 4 and [p["reference_number"] for p in page["items"]] == ["OLD"]


def test_inactive_vendor_still_shows_its_history(client, manager, data, db):
    _, headers = manager
    purchase = received(client, headers, data)
    vendors_service.set_active(db, actor=None, vendor=vendors_service.get_vendor(db, data["acme"]), active=False)

    rows = listed(client, headers, vendor_id=data["acme"])["items"]

    assert [p["id"] for p in rows] == [purchase["id"]]
    assert rows[0]["vendor"]["status"] == "inactive"
    assert client.get(f"{PURCHASES}/{purchase['id']}", headers=headers).status_code == 200


def test_vendor_with_no_purchases_has_an_empty_history(client, manager, data):
    _, headers = manager
    assert listed(client, headers, vendor_id=data["gone"]) == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_unknown_vendor_is_404(client, manager):
    _, headers = manager
    response = client.get(PURCHASES, headers=headers, params={"vendor_id": 9999})
    assert response.status_code == 404 and error_code(response) == "vendor_not_found"


# ---- Search and filters (PUR-09) ---------------------------------------------------------------------
def test_search_and_filters_including_the_date_range(client, manager, data):
    _, headers = manager
    d10 = (TODAY - timedelta(days=10)).isoformat()
    d5 = (TODAY - timedelta(days=5)).isoformat()
    received(client, headers, data, reference_number="INV-A", purchase_date=d10)
    draft(client, headers, data, reference_number="INV-B", purchase_date=d5)
    draft(client, headers, data, vendor_id=data["beta"], reference_number="BT-1")
    cancelled = draft(client, headers, data, reference_number="INV-C", purchase_date=d5)
    client.post(f"{PURCHASES}/{cancelled['id']}/cancel", headers=headers)

    assert refs(client, headers, search="inv-a") == ["INV-A"]
    assert refs(client, headers, search="beta") == ["BT-1"]
    assert refs(client, headers, status="received") == ["INV-A"]
    assert refs(client, headers, status="cancelled") == ["INV-C"]
    assert refs(client, headers, vendor_id=data["beta"]) == ["BT-1"]
    # Date range on the purchase date, both days included (D3).
    assert refs(client, headers, date_from=d10, date_to=d10) == ["INV-A"]
    assert refs(client, headers, date_from=d5, sort="purchase_date") == ["INV-B", "INV-C", "BT-1"]
    assert refs(client, headers, date_to=d5, sort="purchase_date") == ["INV-A", "INV-B", "INV-C"]
    assert refs(client, headers, date_from=d5, date_to=d5, status="draft") == ["INV-B"]
    assert refs(client, headers, date_from=(TODAY + timedelta(days=1)).isoformat()) == []
    # Everything together.
    assert refs(client, headers, search="inv", vendor_id=data["acme"], status="received", date_to=d10) == ["INV-A"]


def test_rows_carry_the_history_fields(client, manager, data):
    _, headers = manager
    received(client, headers, data)
    row = listed(client, headers)["items"][0]
    assert {"reference_number", "vendor", "purchase_date", "received_date", "status", "line_count", "total_amount"} <= row.keys()
    assert "lines" not in row


def test_sort_by_received_date(client, manager, data):
    _, headers = manager
    received(client, headers, data, reference_number="R")
    draft(client, headers, data, reference_number="D")
    assert refs(client, headers, sort="received_date")[0] == "R"  # drafts (no date) sort last ascending


@pytest.mark.parametrize(
    ("params", "code"),
    [
        ({"date_from": "2026-11-10", "date_to": "2026-11-09"}, "invalid_date_range"),
        ({"date_from": "10/11/2026"}, "validation_error"),
        ({"date_to": "not-a-date"}, "validation_error"),
    ],
)
def test_bad_date_range_is_refused(client, manager, params, code):
    _, headers = manager
    response = client.get(PURCHASES, headers=headers, params=params)
    assert response.status_code == 422 and error_code(response) == code


# ---- Roles: Admin and IT Manager only -------------------------------------------------------------
@pytest.mark.parametrize(
    "url", [PURCHASES, f"{PURCHASES}?vendor_id=1", f"{PURCHASES}?date_from=2026-01-01", f"{PURCHASES}/1"]
)
def test_employee_gets_403_and_anonymous_401(client, staff_headers, url):
    _, headers = staff_headers("Employee")
    response = client.get(url, headers=headers)
    assert response.status_code == 403 and error_code(response) == "forbidden"
    assert client.get(url).status_code == 401


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_read_the_history(client, staff_headers, data, role):
    _, headers = staff_headers(role)
    purchase = received(client, headers, data)
    assert client.get(PURCHASES, headers=headers, params={"vendor_id": data["acme"]}).status_code == 200
    assert client.get(f"{PURCHASES}/{purchase['id']}", headers=headers).status_code == 200
