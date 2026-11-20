"""Asset register (Slice 4.1: AST-02, AST-03, AST-05; decisions in decisions.md section 18).

Reading only: the asset list (search by asset ID, serial number or name; filters
category, status and location; sorting and server-side paging), the locations in
use, one asset with its purchase, and the asset's history (its audit log rows).

Done-check (build plan): any asset can be found by ID, serial or name."""

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.assets.models import Asset
from app.modules.categories import service as categories_service
from app.modules.purchases.service import _today
from app.modules.users.models import User
from tests.test_purchases_api import (  # noqa: F401  (pytest fixtures used by name)
    create,
    data,
    error_code,
    laptop_line,
    manager,
    staff_headers,
)
from tests.test_receive_serialized import receipt, receive, unit

ASSETS = "/api/v1/assets"


def receive_laptops(client, headers, data, units, reference="INV-2026-0042", description="Laptops: Dell Latitude 5440"):
    """Receive one purchase of len(units) laptops; returns the received purchase (JSON)."""
    response = create(
        client, headers, data, reference_number=reference,
        lines=[laptop_line(data["laptops"], quantity=len(units), description=description)],
    )
    assert response.status_code == 201, response.text
    purchase = response.json()
    response = receive(client, headers, purchase, receipt(purchase, units))
    assert response.status_code == 200, response.text
    return response.json()


def add_asset(code_hint: str, *, category_id: int, status: str = "available", location: str | None = None,
              name: str = "Spare monitor", serial: str | None = None) -> int:
    """An asset written straight to the TEST database, for statuses the API cannot set
    yet (assigned, retired, ...) and for a second category. Returns its id."""
    with SessionLocal() as s:
        creator = s.scalars(select(User).order_by(User.id)).first()
        asset = Asset(
            name=name, category_id=category_id, model="P2422H", serial_number=serial or f"MON-{code_hint}",
            status=status, location=location, created_by_user_id=creator.id,
        )
        s.add(asset)
        s.commit()
        return asset.id


@pytest.fixture
def register(client, manager, data, db):
    """Five assets:
    AST-000001..3: laptops received on PUR-000001 (serials DL-1001..3; locations
      "Bangalore Floor 2", "bangalore floor 2", "Chennai"; unit 3 named "CEO laptop").
    AST-000004: monitor (category Monitors), status assigned, location "Chennai".
    AST-000005: monitor (category Monitors), status retired, no location."""
    _, headers = manager
    receive_laptops(client, headers, data, [
        unit("DL-1001", location="Bangalore Floor 2"),
        unit("DL-1002", location="bangalore floor 2"),
        unit("DL-1003", location="Chennai", name="CEO laptop"),
    ])
    monitors = categories_service.create_category(db, name="Monitors", tracking_type="serialized")
    add_asset("1", category_id=monitors.id, status="assigned", location="Chennai")
    add_asset("2", category_id=monitors.id, status="retired")
    return {"headers": headers, "monitors": monitors.id, **data}


def listed(client, headers, **params):
    response = client.get(ASSETS, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def codes(client, headers, **params):
    return [a["asset_code"] for a in listed(client, headers, **params)["items"]]


# ---- Done-check: any asset can be found by ID, serial or name --------------------------------------
@pytest.mark.parametrize(
    "term, expected",
    [
        ("AST-000002", ["AST-000002"]),  # asset ID, exact
        ("ast-000002", ["AST-000002"]),  # any case
        ("000003", ["AST-000003"]),  # part of the asset ID
        ("DL-1001", ["AST-000001"]),  # serial number
        ("dl-100", ["AST-000003", "AST-000002", "AST-000001"]),  # part of a serial, any case
        ("ceo LAPTOP", ["AST-000003"]),  # name, any case
        ("latitude", ["AST-000002", "AST-000001"]),  # part of the name (the line's description, B57)
        ("  DL-1002  ", ["AST-000002"]),  # spaces around the term are ignored
        ("nothing-like-this", []),
    ],
)
def test_any_asset_can_be_found_by_id_serial_or_name(client, register, term, expected):
    assert codes(client, register["headers"], search=term) == expected


def test_search_does_not_match_other_fields(client, register):
    # "P2422H" is the monitors' model and "Chennai" a location: neither is searched.
    assert codes(client, register["headers"], search="P2422H") == []
    assert codes(client, register["headers"], search="Chennai") == []


def test_search_treats_percent_and_underscore_as_plain_characters(client, register):
    assert codes(client, register["headers"], search="%") == []
    assert codes(client, register["headers"], search="DL_1001") == []


# ---- List shape and default order --------------------------------------------------------------------
def test_list_returns_every_asset_newest_asset_id_first_with_row_fields(client, register):
    page = listed(client, register["headers"])

    assert page["total"] == 5 and page["page"] == 1 and page["page_size"] == 20
    assert [a["asset_code"] for a in page["items"]] == [f"AST-00000{i}" for i in (5, 4, 3, 2, 1)]
    first_laptop = page["items"][-1]
    assert first_laptop["name"] == "Laptops: Dell Latitude 5440"
    assert first_laptop["category"]["name"] == "Laptops"
    assert first_laptop["serial_number"] == "DL-1001"
    assert first_laptop["model"] == "Latitude 5440"
    assert first_laptop["status"] == "available"
    assert first_laptop["location"] == "Bangalore Floor 2"
    assert set(first_laptop) >= {"id", "brand", "warranty_expiry", "created_at"}


def test_empty_register_is_an_empty_page(client, manager, data):
    _, headers = manager
    assert listed(client, headers) == {"items": [], "total": 0, "page": 1, "page_size": 20}


# ---- Filters -----------------------------------------------------------------------------------------
def test_filter_by_category(client, register):
    h = register["headers"]
    assert codes(client, h, category_id=register["laptops"]) == ["AST-000003", "AST-000002", "AST-000001"]
    assert codes(client, h, category_id=register["monitors"]) == ["AST-000005", "AST-000004"]


def test_filter_by_inactive_category_still_lists_its_assets(client, register, db):
    monitors = categories_service.get_category(db, register["monitors"])
    categories_service.set_active(db, actor=None, category=monitors, active=False)
    assert codes(client, register["headers"], category_id=register["monitors"]) == ["AST-000005", "AST-000004"]


@pytest.mark.parametrize(
    "status, expected",
    [
        ("available", ["AST-000003", "AST-000002", "AST-000001"]),
        ("assigned", ["AST-000004"]),
        ("retired", ["AST-000005"]),
        ("under_maintenance", []),
        ("damaged", []),
    ],
)
def test_filter_by_status(client, register, status, expected):
    assert codes(client, register["headers"], status=status) == expected


def test_filter_by_location_is_the_whole_location_ignoring_case(client, register):
    h = register["headers"]
    assert codes(client, h, location="BANGALORE FLOOR 2") == ["AST-000002", "AST-000001"]
    assert codes(client, h, location="  chennai ") == ["AST-000004", "AST-000003"]
    assert codes(client, h, location="Bangalore") == []  # part of a location does not match


def test_filters_and_search_combine(client, register):
    h = register["headers"]
    assert codes(client, h, location="Chennai", status="available") == ["AST-000003"]
    assert codes(client, h, location="Chennai", category_id=register["monitors"]) == ["AST-000004"]
    assert codes(client, h, search="dl-", location="chennai") == ["AST-000003"]
    assert codes(client, h, status="retired", category_id=register["laptops"]) == []


def test_unknown_category_gives_404_in_the_shared_error_format(client, register):
    response = client.get(ASSETS, headers=register["headers"], params={"category_id": 99999})

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "category_not_found"
    assert body["error"]["message"]


@pytest.mark.parametrize(
    "params",
    [{"status": "lost"}, {"status": "Available"}, {"category_id": "abc"}, {"category_id": 0}, {"page": 0}, {"page_size": 101}],
)
def test_bad_filter_values_give_422_in_the_shared_error_format(client, register, params):
    response = client.get(ASSETS, headers=register["headers"], params=params)

    assert response.status_code == 422
    assert error_code(response) == "validation_error"


def test_locations_in_use_are_listed_once_each_a_to_z(client, register):
    response = client.get(f"{ASSETS}/locations", headers=register["headers"])

    assert response.status_code == 200
    locations = response.json()
    assert [loc.lower() for loc in locations] == ["bangalore floor 2", "chennai"]  # one spelling per location


# ---- Sorting and paging ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "sort, expected",
    [
        ("asset_code", ["AST-000001", "AST-000002", "AST-000003", "AST-000004", "AST-000005"]),
        ("serial_number", ["AST-000001", "AST-000002", "AST-000003", "AST-000004", "AST-000005"]),
        ("-serial_number", ["AST-000005", "AST-000004", "AST-000003", "AST-000002", "AST-000001"]),
        # Same name / status: ties are broken by id in the same direction.
        ("name", ["AST-000003", "AST-000001", "AST-000002", "AST-000004", "AST-000005"]),
        ("status", ["AST-000004", "AST-000001", "AST-000002", "AST-000003", "AST-000005"]),
        ("-category", ["AST-000005", "AST-000004", "AST-000003", "AST-000002", "AST-000001"]),
    ],
)
def test_sortable_columns(client, register, sort, expected):
    assert codes(client, register["headers"], sort=sort) == expected


def test_unknown_sort_field_gives_400_invalid_sort(client, register):
    response = client.get(ASSETS, headers=register["headers"], params={"sort": "cost"})

    assert response.status_code == 400
    assert error_code(response) == "invalid_sort"
    assert "asset_code" in response.json()["error"]["details"]["allowed"]


def test_paging_never_repeats_or_skips_a_row(client, register):
    h = register["headers"]
    pages = [listed(client, h, page=n, page_size=2, sort="status") for n in (1, 2, 3)]

    assert [p["total"] for p in pages] == [5, 5, 5]
    seen = [a["asset_code"] for p in pages for a in p["items"]]
    assert len(seen) == 5 and len(set(seen)) == 5
    assert listed(client, h, page=4, page_size=2)["items"] == []


# ---- One asset (the asset page) ----------------------------------------------------------------------
def test_one_asset_by_id_or_asset_id_shows_details_purchase_and_who_created_it(client, manager, register):
    user, headers = manager
    by_code = client.get(f"{ASSETS}/ast-000001", headers=headers)
    assert by_code.status_code == 200
    asset = by_code.json()
    assert client.get(f"{ASSETS}/{asset['id']}", headers=headers).json() == asset

    assert asset["asset_code"] == "AST-000001" and asset["serial_number"] == "DL-1001"
    assert asset["purchase"]["purchase_number"] == "PUR-000001"
    assert asset["purchase"]["vendor"] == "Acme IT Supplies"
    assert asset["purchase"]["vendor_id"] == register["acme"]
    assert asset["purchase"]["reference_number"] == "INV-2026-0042"
    assert asset["purchase_date"] == _today().isoformat()
    assert asset["cost"] == "85000.00"
    assert asset["created_by"] == {"id": user.id, "email": user.email}
    assert asset["created_at"]


def test_asset_without_a_purchase_has_an_empty_purchase(client, register):
    asset = client.get(f"{ASSETS}/AST-000004", headers=register["headers"]).json()
    assert asset["purchase"] is None and asset["cost"] is None and asset["purchase_date"] is None


@pytest.mark.parametrize("ref", ["99999", "AST-999999", "locations-x", "abc"])
def test_unknown_asset_gives_404(client, register, ref):
    response = client.get(f"{ASSETS}/{ref}", headers=register["headers"])

    assert response.status_code == 404
    assert error_code(response) == "asset_not_found"


# ---- History (the asset's audit log rows) ------------------------------------------------------------
def test_history_lists_the_assets_audit_rows_with_who_did_it(client, manager, register):
    user, headers = manager

    response = client.get(f"{ASSETS}/AST-000002/history", headers=headers)

    assert response.status_code == 200
    history = response.json()
    assert history["total"] == 1
    entry = history["items"][0]
    assert entry["action"] == "asset.created"
    assert entry["actor"] == {"id": user.id, "email": user.email}
    assert entry["before"] is None
    assert entry["after"]["asset_code"] == "AST-000002"
    assert entry["after"]["serial_number"] == "DL-1002"
    assert entry["after"]["purchase_number"] == "PUR-000001"
    assert entry["created_at"]


def test_history_shows_only_this_assets_rows_newest_first(client, manager, register):
    _, headers = manager
    # A second receipt writes more asset.created rows, but for other assets.
    receive_laptops(client, headers, register, [unit("DL-2001")], reference="INV-2026-0043")

    first = client.get(f"{ASSETS}/1/history", headers=headers).json()
    assert [e["after"]["asset_code"] for e in first["items"]] == ["AST-000001"]


def test_asset_without_audit_rows_has_an_empty_history(client, register):
    # AST-000004 was written straight to the database (test-only), so it has no audit row.
    history = client.get(f"{ASSETS}/AST-000004/history", headers=register["headers"]).json()
    assert history == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_history_of_unknown_asset_gives_404(client, register):
    response = client.get(f"{ASSETS}/AST-999999/history", headers=register["headers"])
    assert response.status_code == 404
    assert error_code(response) == "asset_not_found"


# ---- Roles -------------------------------------------------------------------------------------------
READ_URLS = [ASSETS, f"{ASSETS}/locations", f"{ASSETS}/AST-000001", f"{ASSETS}/AST-000001/history"]


@pytest.mark.parametrize("url", READ_URLS)
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_read_the_register(client, staff_headers, register, url, role):
    _, headers = staff_headers(role)
    assert client.get(url, headers=headers).status_code == 200


@pytest.mark.parametrize("url", READ_URLS)
def test_employee_role_is_blocked(client, staff_headers, register, url):
    _, headers = staff_headers("Employee")

    response = client.get(url, headers=headers)

    assert response.status_code == 403
    assert error_code(response) == "forbidden"


@pytest.mark.parametrize("url", READ_URLS)
def test_register_needs_login(client, url):
    assert client.get(url).status_code == 401


def test_reading_changes_nothing(client, register):
    with SessionLocal() as s:
        before = [(a.id, a.status, a.updated_at) for a in s.scalars(select(Asset).order_by(Asset.id))]
    h = register["headers"]
    listed(client, h, search="dl")
    client.get(f"{ASSETS}/AST-000001", headers=h)
    client.get(f"{ASSETS}/AST-000001/history", headers=h)
    with SessionLocal() as s:
        after = [(a.id, a.status, a.updated_at) for a in s.scalars(select(Asset).order_by(Asset.id))]
    assert before == after

