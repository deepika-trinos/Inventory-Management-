"""Asset categories API (Slice 2.1, AST-02, PRD 9.2, BR-12, BR-13)."""

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.modules.audit.models import AuditLog
from app.modules.categories import service
from app.modules.categories.models import AssetCategory
from tests.conftest import auth_header

CATEGORIES = "/api/v1/categories"


@pytest.fixture
def staff_headers(make_user, login):
    """Log in as the given role and return (user, headers)."""

    def _headers(role: str = "IT Manager"):
        user, password = make_user(role)
        return user, auth_header(login(user.email, password))

    return _headers


@pytest.fixture
def manager(staff_headers):
    return staff_headers("IT Manager")


def create(client, headers, **body):
    body = {"name": "Laptops", "tracking_type": "serialized", **body}
    return client.post(CATEGORIES, headers=headers, json=body)


def audit_for(category_id: int, action: str | None = None) -> list[AuditLog]:
    with SessionLocal() as fresh:
        stmt = select(AuditLog).where(
            AuditLog.entity_type == "asset_categories", AuditLog.entity_id == str(category_id)
        )
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return list(fresh.scalars(stmt.order_by(AuditLog.id)).all())


def in_database(category_id: int) -> AssetCategory | None:
    with SessionLocal() as fresh:
        return fresh.get(AssetCategory, category_id)


# ---- Roles: Admin and IT Manager only -------------------------------------------------
ENDPOINTS = [
    ("get", CATEGORIES, None),
    ("post", CATEGORIES, {"name": "X", "tracking_type": "bulk"}),
    ("get", f"{CATEGORIES}/1", None),
    ("patch", f"{CATEGORIES}/1", {"name": "Y"}),
    ("post", f"{CATEGORIES}/1/activate", None),
    ("post", f"{CATEGORIES}/1/deactivate", None),
]


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_employee_gets_403_on_every_category_endpoint(client, staff_headers, method, url, body):
    _, headers = staff_headers("Employee")

    response = client.request(method, url, json=body, headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize(("method", "url", "body"), ENDPOINTS)
def test_category_endpoints_need_login(client, method, url, body):
    response = client.request(method, url, json=body)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_use_every_endpoint(client, staff_headers, role):
    _, headers = staff_headers(role)

    created = create(client, headers)
    cid = created.json()["id"]

    assert created.status_code == 201
    assert client.get(CATEGORIES, headers=headers).status_code == 200
    assert client.get(f"{CATEGORIES}/{cid}", headers=headers).status_code == 200
    assert client.patch(f"{CATEGORIES}/{cid}", headers=headers, json={"description": "d"}).status_code == 200
    assert client.post(f"{CATEGORIES}/{cid}/deactivate", headers=headers).status_code == 200
    assert client.post(f"{CATEGORIES}/{cid}/activate", headers=headers).status_code == 200


# ---- Create (done-check: both kinds) ---------------------------------------------------
@pytest.mark.parametrize("tracking_type", ["serialized", "bulk"])
def test_create_both_kinds_writes_audit_row(client, manager, tracking_type):
    user, headers = manager

    response = create(client, headers, name="  Monitors  ", description=" Desk screens ", tracking_type=tracking_type)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Monitors"  # spaces trimmed
    assert body["description"] == "Desk screens"
    assert body["tracking_type"] == tracking_type
    assert body["status"] == "active"
    [row] = audit_for(body["id"], "category.created")
    assert row.actor_user_id == user.id
    assert row.before_data is None
    assert row.after_data == {
        "name": "Monitors",
        "description": "Desk screens",
        "tracking_type": tracking_type,
        "status": "active",
    }


def test_description_is_optional(client, manager):
    _, headers = manager

    response = client.post(CATEGORIES, headers=headers, json={"name": "Cables", "tracking_type": "bulk"})

    assert response.status_code == 201
    assert response.json()["description"] is None


@pytest.mark.parametrize("name", ["Laptops", "LAPTOPS", "laptops", "  lApToPs "])
def test_duplicate_name_is_blocked_in_any_case(client, manager, name):
    _, headers = manager
    assert create(client, headers, name="Laptops").status_code == 201

    response = create(client, headers, name=name, tracking_type="bulk")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_name_taken"


def test_inactive_category_name_still_blocks_duplicates(client, manager):
    _, headers = manager
    cid = create(client, headers, name="Laptops").json()["id"]
    client.post(f"{CATEGORIES}/{cid}/deactivate", headers=headers)

    response = create(client, headers, name="laptops")

    assert response.status_code == 409


def test_database_index_blocks_case_duplicates_even_without_the_service(db):
    """The unique index on lower(name) is the last line of defence."""
    from sqlalchemy.exc import IntegrityError

    db.add(AssetCategory(name="Docks", tracking_type="bulk"))
    db.commit()
    db.add(AssetCategory(name="DOCKS", tracking_type="bulk"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"name": "   ", "tracking_type": "bulk"}, "invalid_name"),
        ({"name": "", "tracking_type": "bulk"}, "validation_error"),
        ({"tracking_type": "bulk"}, "validation_error"),
        ({"name": "Keyboards"}, "validation_error"),
        ({"name": "Keyboards", "tracking_type": "by_weight"}, "validation_error"),
        ({"name": "x" * 101, "tracking_type": "bulk"}, "validation_error"),
        ({"name": "Keyboards", "tracking_type": "bulk", "description": "d" * 501}, "validation_error"),
    ],
)
def test_create_validation(client, manager, body, code):
    _, headers = manager

    response = client.post(CATEGORIES, headers=headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert client.get(CATEGORIES, headers=headers).json()["total"] == 0


def test_database_rejects_unknown_tracking_type_and_status(db):
    from sqlalchemy.exc import IntegrityError

    for bad in (
        AssetCategory(name="A", tracking_type="weight"),
        AssetCategory(name="B", tracking_type="bulk", status="archived"),
    ):
        db.add(bad)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


# ---- Read ----------------------------------------------------------------------------
def test_list_search_filter_sort_and_paging(client, manager):
    _, headers = manager
    for name, kind in [("Laptops", "serialized"), ("Monitors", "serialized"), ("Mice", "bulk"),
                       ("Keyboards", "bulk"), ("Laptop bags", "bulk")]:
        create(client, headers, name=name, tracking_type=kind)
    mice = client.get(CATEGORIES, headers=headers, params={"search": "mice"}).json()["items"][0]
    client.post(f"{CATEGORIES}/{mice['id']}/deactivate", headers=headers)

    def names(**params):
        body = client.get(CATEGORIES, headers=headers, params=params).json()
        return [c["name"] for c in body["items"]], body["total"]

    assert names() == (["Keyboards", "Laptop bags", "Laptops", "Mice", "Monitors"], 5)  # default: name A-Z
    assert names(search="LAPTOP") == (["Laptop bags", "Laptops"], 2)
    assert names(tracking_type="serialized") == (["Laptops", "Monitors"], 2)
    assert names(status="inactive") == (["Mice"], 1)
    assert names(status="active", tracking_type="bulk") == (["Keyboards", "Laptop bags"], 2)
    assert names(sort="-name", page_size=2, page=2) == (["Laptops", "Laptop bags"], 5)
    assert names(search="%") == ([], 0)  # wildcards are treated as plain text


def test_list_rejects_bad_filters_and_sort(client, manager):
    _, headers = manager

    bad_sort = client.get(CATEGORIES, headers=headers, params={"sort": "password"})
    bad_type = client.get(CATEGORIES, headers=headers, params={"tracking_type": "weight"})
    bad_status = client.get(CATEGORIES, headers=headers, params={"status": "deleted"})

    assert bad_sort.status_code == 400
    assert bad_sort.json()["error"]["code"] == "invalid_sort"
    assert bad_type.status_code == 422
    assert bad_status.status_code == 422


def test_get_one_and_not_found(client, manager):
    _, headers = manager
    cid = create(client, headers).json()["id"]

    found = client.get(f"{CATEGORIES}/{cid}", headers=headers)
    missing = client.get(f"{CATEGORIES}/9999", headers=headers)

    assert found.status_code == 200
    assert found.json()["name"] == "Laptops"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "category_not_found"


# ---- Edit (done-check) -------------------------------------------------------------------
def test_edit_name_description_and_tracking_type_writes_audit_row(client, manager):
    user, headers = manager
    cid = create(client, headers, name="Laptop", description="old").json()["id"]

    response = client.patch(
        f"{CATEGORIES}/{cid}",
        headers=headers,
        json={"name": "Laptops", "description": "Company laptops", "tracking_type": "bulk"},
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["description"], body["tracking_type"]) == ("Laptops", "Company laptops", "bulk")
    [row] = audit_for(cid, "category.updated")
    assert row.actor_user_id == user.id
    assert row.before_data == {"name": "Laptop", "description": "old", "tracking_type": "serialized", "status": "active"}
    assert row.after_data == {"name": "Laptops", "description": "Company laptops", "tracking_type": "bulk", "status": "active"}


def test_edit_can_clear_description_and_change_name_case(client, manager):
    _, headers = manager
    cid = create(client, headers, name="laptops", description="x").json()["id"]

    response = client.patch(f"{CATEGORIES}/{cid}", headers=headers, json={"name": "Laptops", "description": None})

    assert response.status_code == 200
    assert response.json()["name"] == "Laptops"  # its own name in another case is fine
    assert response.json()["description"] is None


def test_edit_with_no_real_change_writes_no_audit_row(client, manager):
    _, headers = manager
    cid = create(client, headers, description="same").json()["id"]

    response = client.patch(
        f"{CATEGORIES}/{cid}", headers=headers,
        json={"name": " Laptops ", "description": "same", "tracking_type": "serialized"},
    )

    assert response.status_code == 200
    assert audit_for(cid, "category.updated") == []


def test_edit_to_another_categorys_name_is_blocked(client, manager):
    _, headers = manager
    create(client, headers, name="Mice", tracking_type="bulk")
    cid = create(client, headers, name="Keyboards", tracking_type="bulk").json()["id"]

    response = client.patch(f"{CATEGORIES}/{cid}", headers=headers, json={"name": "MICE"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_name_taken"
    assert in_database(cid).name == "Keyboards"
    assert audit_for(cid, "category.updated") == []


@pytest.mark.parametrize(
    ("body", "status_code", "code"),
    [
        ({"name": "  "}, 422, "invalid_name"),
        ({"name": ""}, 422, "validation_error"),
        ({"tracking_type": "weight"}, 422, "validation_error"),
        ({"status": "inactive"}, 200, None),  # unknown fields are ignored: status has its own actions
    ],
)
def test_edit_validation(client, manager, body, status_code, code):
    _, headers = manager
    cid = create(client, headers).json()["id"]

    response = client.patch(f"{CATEGORIES}/{cid}", headers=headers, json=body)

    assert response.status_code == status_code
    if code:
        assert response.json()["error"]["code"] == code
    assert in_database(cid).status == "active"


def test_edit_missing_category_is_404(client, manager):
    _, headers = manager
    response = client.patch(f"{CATEGORIES}/9999", headers=headers, json={"name": "X"})
    assert response.status_code == 404


def test_tracking_type_is_locked_once_the_category_is_in_use(client, manager, monkeypatch):
    """Nothing can use a category until Slice 2.4 / 3.2, so we pretend it is in use."""
    _, headers = manager
    cid = create(client, headers, description="old").json()["id"]
    monkeypatch.setattr(service, "_category_in_use", lambda db, category: True)

    locked = client.patch(f"{CATEGORIES}/{cid}", headers=headers, json={"tracking_type": "bulk"})
    other_edit = client.patch(f"{CATEGORIES}/{cid}", headers=headers, json={"description": "new"})

    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "tracking_type_locked"
    assert in_database(cid).tracking_type == "serialized"
    assert other_edit.status_code == 200  # name/description can still be edited
    assert [r.after_data["description"] for r in audit_for(cid, "category.updated")] == ["new"]


def test_tracking_type_guard_does_not_apply_yet(db):
    """Until Slice 2.4 / 3.2 nothing uses a category, so the guard never fires."""
    category = service.create_category(db, name="Phones", tracking_type="serialized")
    assert service._category_in_use(db, category) is False


# ---- Deactivate / activate, never delete (BR-12) -------------------------------------------
def test_deactivate_and_activate_write_audit_rows(client, manager):
    user, headers = manager
    cid = create(client, headers).json()["id"]

    off = client.post(f"{CATEGORIES}/{cid}/deactivate", headers=headers)
    still_readable = client.get(f"{CATEGORIES}/{cid}", headers=headers)
    on = client.post(f"{CATEGORIES}/{cid}/activate", headers=headers)

    assert off.status_code == 200 and off.json()["status"] == "inactive"
    assert still_readable.status_code == 200 and still_readable.json()["status"] == "inactive"
    assert on.status_code == 200 and on.json()["status"] == "active"
    [deactivated] = audit_for(cid, "category.deactivated")
    [activated] = audit_for(cid, "category.activated")
    assert deactivated.actor_user_id == user.id
    assert (deactivated.before_data["status"], deactivated.after_data["status"]) == ("active", "inactive")
    assert (activated.before_data["status"], activated.after_data["status"]) == ("inactive", "active")


def test_repeating_activate_or_deactivate_changes_nothing(client, manager):
    _, headers = manager
    cid = create(client, headers).json()["id"]

    client.post(f"{CATEGORIES}/{cid}/activate", headers=headers)  # already active
    client.post(f"{CATEGORIES}/{cid}/deactivate", headers=headers)
    client.post(f"{CATEGORIES}/{cid}/deactivate", headers=headers)  # already inactive

    assert [r.action for r in audit_for(cid)] == ["category.created", "category.deactivated"]


def test_inactive_category_can_still_be_edited(client, manager):
    _, headers = manager
    cid = create(client, headers).json()["id"]
    client.post(f"{CATEGORIES}/{cid}/deactivate", headers=headers)

    response = client.patch(f"{CATEGORIES}/{cid}", headers=headers, json={"description": "old models"})

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


def test_activate_or_deactivate_missing_category_is_404(client, manager):
    _, headers = manager
    assert client.post(f"{CATEGORIES}/9999/deactivate", headers=headers).status_code == 404
    assert client.post(f"{CATEGORIES}/9999/activate", headers=headers).status_code == 404


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_there_is_no_delete(client, staff_headers, role):
    _, headers = staff_headers(role)
    cid = create(client, headers).json()["id"]

    response = client.delete(f"{CATEGORIES}/{cid}", headers=headers)

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
    assert in_database(cid) is not None
    assert not hasattr(service, "delete_category")


def test_ensure_category_selectable_blocks_inactive_categories(db):
    """Helper for Slice 2.4 onward: a deactivated category cannot be picked for new records."""
    active = service.create_category(db, name="Mice", tracking_type="bulk")
    inactive = service.create_category(db, name="Old mice", tracking_type="bulk")
    service.set_active(db, actor=None, category=inactive, active=False)

    assert service.ensure_category_selectable(db, active.id).id == active.id
    with pytest.raises(AppError) as blocked:
        service.ensure_category_selectable(db, inactive.id)
    assert (blocked.value.status_code, blocked.value.code) == (409, "category_inactive")
    with pytest.raises(AppError) as missing:
        service.ensure_category_selectable(db, 9999)
    assert missing.value.status_code == 404


def test_failed_audit_write_saves_nothing(db, monkeypatch):
    """The change and its audit row are saved together or not at all."""
    from app.modules.audit import service as audit

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit is down")

    monkeypatch.setattr(audit, "record", broken_record)
    with pytest.raises(RuntimeError):
        service.create_category(db, name="Headsets", tracking_type="bulk")

    with SessionLocal() as fresh:
        assert fresh.scalars(select(AssetCategory)).all() == []
