"""Vendors API (Slice 2.3, VEN-01 to VEN-03, VEN-05, BR-12, BR-13, decisions B30-B31)."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.modules.audit.models import AuditLog
from app.modules.vendors import service
from app.modules.vendors.models import Vendor
from tests.conftest import auth_header

VENDORS = "/api/v1/vendors"


@pytest.fixture
def staff_headers(make_user, login):
    def _headers(role: str = "IT Manager"):
        user, password = make_user(role)
        return user, auth_header(login(user.email, password))

    return _headers


@pytest.fixture
def manager(staff_headers):
    return staff_headers("IT Manager")


def create(client, headers, **body):
    body = {"name": "Acme IT Supplies", **body}
    return client.post(VENDORS, headers=headers, json=body)


def audit_for(vendor_id: int, action: str | None = None) -> list[AuditLog]:
    with SessionLocal() as fresh:
        stmt = select(AuditLog).where(AuditLog.entity_type == "vendors", AuditLog.entity_id == str(vendor_id))
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return list(fresh.scalars(stmt.order_by(AuditLog.id)).all())


def in_database(vendor_id: int) -> Vendor | None:
    with SessionLocal() as fresh:
        return fresh.get(Vendor, vendor_id)


# ---- Roles: Admin and IT Manager only -------------------------------------------------
ENDPOINTS = [
    ("get", VENDORS, None),
    ("post", VENDORS, {"name": "X"}),
    ("get", f"{VENDORS}/1", None),
    ("patch", f"{VENDORS}/1", {"name": "Y"}),
    ("post", f"{VENDORS}/1/activate", None),
    ("post", f"{VENDORS}/1/deactivate", None),
]


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_employee_role_gets_403_on_every_vendor_endpoint(client, staff_headers, method, url, body):
    _, headers = staff_headers("Employee")

    response = client.request(method, url, json=body, headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_vendor_endpoints_need_login(client, method, url, body):
    assert client.request(method, url, json=body).status_code == 401


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_use_every_endpoint(client, staff_headers, role):
    _, headers = staff_headers(role)

    created = create(client, headers)
    vid = created.json()["id"]

    assert created.status_code == 201
    assert client.get(VENDORS, headers=headers).status_code == 200
    assert client.get(f"{VENDORS}/{vid}", headers=headers).status_code == 200
    assert client.patch(f"{VENDORS}/{vid}", headers=headers, json={"phone": "12345"}).status_code == 200
    assert client.post(f"{VENDORS}/{vid}/deactivate", headers=headers).status_code == 200
    assert client.post(f"{VENDORS}/{vid}/activate", headers=headers).status_code == 200


# ---- Done-check: added, found and deactivated, but not deleted --------------------------
def test_vendor_is_added_found_and_deactivated(client, manager):
    user, headers = manager

    created = create(
        client, headers, name="  Acme IT Supplies ", contact_person=" Priya Nair ",
        email=" Sales@Acme.Example.COM ", phone="+91 80 1234 5678", address="12 MG Road\nBengaluru",
    )
    vid = created.json()["id"]
    found = client.get(VENDORS, headers=headers, params={"search": "acme"}).json()
    off = client.post(f"{VENDORS}/{vid}/deactivate", headers=headers)
    still_readable = client.get(f"{VENDORS}/{vid}", headers=headers)

    assert created.status_code == 201
    body = created.json()
    assert (body["name"], body["contact_person"]) == ("Acme IT Supplies", "Priya Nair")
    assert body["email"] == "sales@acme.example.com"  # lower case (B5)
    assert (body["phone"], body["address"], body["status"]) == ("+91 80 1234 5678", "12 MG Road\nBengaluru", "active")
    assert [v["id"] for v in found["items"]] == [vid]
    assert off.status_code == 200 and off.json()["status"] == "inactive"
    assert still_readable.status_code == 200 and still_readable.json()["status"] == "inactive"

    [created_row] = audit_for(vid, "vendor.created")
    [off_row] = audit_for(vid, "vendor.deactivated")
    assert created_row.actor_user_id == user.id and created_row.before_data is None
    assert created_row.after_data["email"] == "sales@acme.example.com"
    assert off_row.actor_user_id == user.id
    assert (off_row.before_data["status"], off_row.after_data["status"]) == ("active", "inactive")


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_there_is_no_delete(client, staff_headers, role):
    _, headers = staff_headers(role)
    vid = create(client, headers).json()["id"]

    response = client.delete(f"{VENDORS}/{vid}", headers=headers)

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
    assert in_database(vid) is not None
    assert not hasattr(service, "delete_vendor")


def test_only_the_name_is_required(client, manager):
    _, headers = manager

    response = client.post(VENDORS, headers=headers, json={"name": "Bare Vendor"})

    assert response.status_code == 201
    body = response.json()
    assert [body[f] for f in ("contact_person", "email", "phone", "address")] == [None, None, None, None]


def test_blank_optional_fields_are_stored_as_empty(client, manager):
    _, headers = manager

    response = create(client, headers, contact_person="  ", email="", phone=" ", address="   ")

    assert response.status_code == 201
    assert [response.json()[f] for f in ("contact_person", "email", "phone", "address")] == [None] * 4


# ---- Duplicates (B30, B31) ----------------------------------------------------------------
@pytest.mark.parametrize("name", ["Acme IT Supplies", "ACME it supplies", "  acme IT Supplies "])
def test_duplicate_name_is_blocked_in_any_case(client, manager, name):
    _, headers = manager
    assert create(client, headers).status_code == 201

    response = create(client, headers, name=name)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "vendor_name_taken"


def test_inactive_vendor_name_still_blocks_duplicates(client, manager):
    _, headers = manager
    vid = create(client, headers).json()["id"]
    client.post(f"{VENDORS}/{vid}/deactivate", headers=headers)

    assert create(client, headers, name="acme it supplies").status_code == 409


def test_email_may_repeat_across_vendors(client, manager):
    _, headers = manager
    create(client, headers, name="Acme North", email="sales@acme.example.com")

    response = create(client, headers, name="Acme South", email="SALES@acme.example.com")

    assert response.status_code == 201


def test_database_index_blocks_case_duplicates_even_without_the_service(db):
    db.add(Vendor(name="Zed Corp"))
    db.commit()
    db.add(Vendor(name="ZED CORP"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_database_rejects_upper_case_email_and_unknown_status(db):
    for bad in (Vendor(name="A", email="Upper@Example.com"), Vendor(name="B", status="archived")):
        db.add(bad)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


# ---- Validation ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"name": "   "}, "invalid_name"),
        ({"name": ""}, "validation_error"),
        ({}, "validation_error"),
        ({"contact_person": "Only Contact"}, "validation_error"),
        ({"name": "V", "email": "not-an-email"}, "invalid_email"),
        ({"name": "V", "email": "a@b"}, "invalid_email"),
        ({"name": "V", "phone": "call us"}, "invalid_phone"),
        ({"name": "x" * 151}, "validation_error"),
        ({"name": "V", "address": "a" * 501}, "validation_error"),
        ({"name": "V", "phone": "1" * 31}, "validation_error"),
    ],
)
def test_create_validation(client, manager, body, code):
    _, headers = manager

    response = client.post(VENDORS, headers=headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert client.get(VENDORS, headers=headers).json()["total"] == 0


# ---- Search, filter, sort, paging (VEN-03) -------------------------------------------------
@pytest.fixture
def sample(client, manager):
    _, headers = manager
    rows = [
        {"name": "Acme IT Supplies", "contact_person": "Priya Nair", "email": "sales@acme.example.com", "phone": "080-1111"},
        {"name": "Bright Cables", "contact_person": "Karan Mehta", "email": "hello@bright.example.com", "phone": "022-2222"},
        {"name": "Delta Peripherals", "contact_person": "Asha Rao", "email": "orders@delta.example.com"},
        {"name": "Old Parts Co", "contact_person": "Ravi Shah", "phone": "011-3333"},
    ]
    ids = {r["name"]: client.post(VENDORS, headers=headers, json=r).json()["id"] for r in rows}
    client.post(f"{VENDORS}/{ids['Old Parts Co']}/deactivate", headers=headers)
    return headers


def names(client, headers, **params):
    return [v["name"] for v in client.get(VENDORS, headers=headers, params=params).json()["items"]]


@pytest.mark.parametrize(
    ("search", "expected"),
    [
        ("BRIGHT", ["Bright Cables"]),  # by name
        ("asha", ["Delta Peripherals"]),  # by contact person
        ("orders@", ["Delta Peripherals"]),  # by email
        ("ACME.example", ["Acme IT Supplies"]),  # email search ignores case
        ("022-", ["Bright Cables"]),  # by phone
        ("%", []),  # wildcards are plain text
    ],
)
def test_search_by_name_contact_email_or_phone(client, sample, search, expected):
    assert names(client, sample, search=search) == expected


def test_status_filter_sort_and_paging(client, sample):
    headers = sample

    assert names(client, headers) == ["Acme IT Supplies", "Bright Cables", "Delta Peripherals", "Old Parts Co"]
    assert names(client, headers, status="inactive") == ["Old Parts Co"]
    assert names(client, headers, status="active", sort="-name") == ["Delta Peripherals", "Bright Cables", "Acme IT Supplies"]
    assert names(client, headers, sort="contact_person") == [
        "Delta Peripherals", "Bright Cables", "Acme IT Supplies", "Old Parts Co"
    ]
    page = client.get(VENDORS, headers=headers, params={"page": 2, "page_size": 3}).json()
    assert (page["total"], page["page"], [v["name"] for v in page["items"]]) == (4, 2, ["Old Parts Co"])


def test_list_rejects_bad_sort_and_status(client, manager):
    _, headers = manager

    bad_sort = client.get(VENDORS, headers=headers, params={"sort": "address"})
    bad_status = client.get(VENDORS, headers=headers, params={"status": "deleted"})

    assert bad_sort.status_code == 400 and bad_sort.json()["error"]["code"] == "invalid_sort"
    assert bad_status.status_code == 422


def test_get_unknown_vendor_is_404(client, manager):
    _, headers = manager
    response = client.get(f"{VENDORS}/9999", headers=headers)
    assert response.status_code == 404 and response.json()["error"]["code"] == "vendor_not_found"


# ---- Edit ---------------------------------------------------------------------------------
def test_edit_writes_audit_row_with_before_and_after(client, manager):
    user, headers = manager
    vid = create(client, headers, contact_person="Priya", phone="080-1111").json()["id"]

    response = client.patch(
        f"{VENDORS}/{vid}", headers=headers,
        json={"name": "Acme IT Supplies Pvt Ltd", "email": "New@Acme.example.com", "phone": None},
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["email"], body["phone"], body["contact_person"]) == (
        "Acme IT Supplies Pvt Ltd", "new@acme.example.com", None, "Priya"
    )
    [row] = audit_for(vid, "vendor.updated")
    assert row.actor_user_id == user.id
    assert (row.before_data["name"], row.after_data["name"]) == ("Acme IT Supplies", "Acme IT Supplies Pvt Ltd")
    assert (row.before_data["phone"], row.after_data["phone"]) == ("080-1111", None)


def test_edit_with_no_real_change_writes_no_audit_row(client, manager):
    _, headers = manager
    vid = create(client, headers, email="sales@acme.example.com").json()["id"]

    response = client.patch(
        f"{VENDORS}/{vid}", headers=headers, json={"name": " Acme IT Supplies ", "email": "SALES@acme.example.com"}
    )

    assert response.status_code == 200
    assert audit_for(vid, "vendor.updated") == []


def test_edit_name_rules(client, manager):
    _, headers = manager
    create(client, headers, name="Bright Cables")
    vid = create(client, headers).json()["id"]

    clash = client.patch(f"{VENDORS}/{vid}", headers=headers, json={"name": "BRIGHT CABLES"})
    own_case = client.patch(f"{VENDORS}/{vid}", headers=headers, json={"name": "ACME IT SUPPLIES"})
    keep = client.patch(f"{VENDORS}/{vid}", headers=headers, json={"name": None})

    assert clash.status_code == 409 and clash.json()["error"]["code"] == "vendor_name_taken"
    assert own_case.status_code == 200 and own_case.json()["name"] == "ACME IT SUPPLIES"
    assert keep.status_code == 200 and keep.json()["name"] == "ACME IT SUPPLIES"


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"name": "  "}, "invalid_name"),
        ({"name": ""}, "validation_error"),
        ({"email": "nope"}, "invalid_email"),
        ({"phone": "abc"}, "invalid_phone"),
    ],
)
def test_edit_validation(client, manager, body, code):
    _, headers = manager
    vid = create(client, headers).json()["id"]

    response = client.patch(f"{VENDORS}/{vid}", headers=headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert in_database(vid).name == "Acme IT Supplies"


def test_inactive_vendor_can_still_be_edited(client, manager):
    _, headers = manager
    vid = create(client, headers).json()["id"]
    client.post(f"{VENDORS}/{vid}/deactivate", headers=headers)

    response = client.patch(f"{VENDORS}/{vid}", headers=headers, json={"address": "Moved"})

    assert response.status_code == 200 and response.json()["status"] == "inactive"


def test_edit_missing_vendor_is_404(client, manager):
    _, headers = manager
    assert client.patch(f"{VENDORS}/9999", headers=headers, json={"name": "X"}).status_code == 404


# ---- Activate / deactivate ----------------------------------------------------------------
def test_activate_and_repeat_actions(client, manager):
    _, headers = manager
    vid = create(client, headers).json()["id"]

    client.post(f"{VENDORS}/{vid}/activate", headers=headers)  # already active: nothing
    client.post(f"{VENDORS}/{vid}/deactivate", headers=headers)
    client.post(f"{VENDORS}/{vid}/deactivate", headers=headers)  # already inactive: nothing
    on = client.post(f"{VENDORS}/{vid}/activate", headers=headers)

    assert on.json()["status"] == "active"
    assert [r.action for r in audit_for(vid)] == ["vendor.created", "vendor.deactivated", "vendor.activated"]
    [activated] = audit_for(vid, "vendor.activated")
    assert (activated.before_data["status"], activated.after_data["status"]) == ("inactive", "active")


def test_activate_or_deactivate_missing_vendor_is_404(client, manager):
    _, headers = manager
    assert client.post(f"{VENDORS}/9999/deactivate", headers=headers).status_code == 404
    assert client.post(f"{VENDORS}/9999/activate", headers=headers).status_code == 404


# ---- Active-vendor check for Slice 3.1 ------------------------------------------------------
def test_ensure_vendor_active(db):
    active = service.create_vendor(db, data={"name": "Active Vendor"})
    inactive = service.create_vendor(db, data={"name": "Gone Vendor"})
    service.set_active(db, actor=None, vendor=inactive, active=False)

    assert service.ensure_vendor_active(db, active.id).id == active.id
    with pytest.raises(AppError) as blocked:
        service.ensure_vendor_active(db, inactive.id)
    assert (blocked.value.status_code, blocked.value.code) == (409, "vendor_inactive")
    with pytest.raises(AppError) as missing:
        service.ensure_vendor_active(db, 9999)
    assert missing.value.status_code == 404


def test_failed_audit_write_saves_nothing(db, monkeypatch):
    from app.modules.audit import service as audit

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit is down")

    monkeypatch.setattr(audit, "record", broken_record)
    with pytest.raises(RuntimeError):
        service.create_vendor(db, data={"name": "No Audit"})

    with SessionLocal() as fresh:
        assert fresh.scalars(select(Vendor)).all() == []
