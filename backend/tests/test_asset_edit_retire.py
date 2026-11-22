"""Edit and retire assets (Slice 4.2: AST-04, AST-07, BR-13; owner's answers A2, A3;
decisions in decisions.md section 20).

- PATCH /assets/{ref}: only name, brand, model, serial number (still unique), location
  and warranty expiry; status and the purchase facts are refused (validation error).
- POST /assets/{ref}/retire: only from Available or Damaged, with a required reason
  (up to 500 characters); a retired asset can be neither edited nor retired again.
- Each change writes its audit row in the same transaction; a failure saves nothing.

Done-check (build plan): a retired asset shows its reason in history and can no longer
be edited back to Available."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.assets.models import Asset
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditLog
from tests.test_asset_register import receive_laptops
from tests.test_purchases_api import (  # noqa: F401  (pytest fixtures used by name)
    data,
    error_code,
    manager,
    staff_headers,
)
from tests.test_receive_serialized import unit

ASSETS = "/api/v1/assets"


@pytest.fixture
def laptops(client, manager, data):
    """AST-000001 (DL-1001) and AST-000002 (DL-1002), received today on PUR-000001,
    warranty 2029-11-10 on unit 1, location "Bangalore Floor 2" on unit 1."""
    _, headers = manager
    receive_laptops(client, headers, data, [
        unit("DL-1001", brand="Dell", location="Bangalore Floor 2", warranty_expiry="2029-11-10"),
        unit("DL-1002"),
    ])
    return headers


def stored(code: str) -> Asset:
    with SessionLocal() as s:
        asset = s.scalars(select(Asset).where(Asset.asset_code == code)).one()
        s.expunge(asset)
        return asset


def audit_rows(code: str, action: str | None = None) -> list[AuditLog]:
    with SessionLocal() as s:
        asset_id = s.scalars(select(Asset.id).where(Asset.asset_code == code)).one()
        stmt = select(AuditLog).where(AuditLog.entity_type == "assets", AuditLog.entity_id == str(asset_id))
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return list(s.scalars(stmt.order_by(AuditLog.id)).all())


def set_status(code: str, status: str) -> None:
    """Statuses the API cannot set yet (assign: Phase 5, maintenance: Phase 6) - test-only shortcut."""
    with SessionLocal() as s:
        s.execute(text("UPDATE assets SET status = :st WHERE asset_code = :c"), {"st": status, "c": code})
        s.commit()


def edit(client, headers, code, **body):
    return client.patch(f"{ASSETS}/{code}", headers=headers, json=body)


def retire(client, headers, code, reason="Screen cracked beyond repair"):
    return client.post(f"{ASSETS}/{code}/retire", headers=headers, json={"reason": reason})


# ---- Editing: each editable field ---------------------------------------------------------------
@pytest.mark.parametrize(
    "field, value, expected",
    [
        ("name", "  Finance team laptop  ", "Finance team laptop"),  # spaces trimmed
        ("brand", "Dell Technologies", "Dell Technologies"),
        ("model", "Latitude 5450", "Latitude 5450"),
        ("serial_number", "DL-1001-A", "DL-1001-A"),
        ("location", "Chennai", "Chennai"),
        ("warranty_expiry", "2030-01-31", "2030-01-31"),
    ],
)
def test_each_editable_field_can_be_changed_and_is_audited(client, manager, laptops, field, value, expected):
    user, headers = manager
    before = getattr(stored("AST-000001"), field)

    response = edit(client, headers, "AST-000001", **{field: value})

    assert response.status_code == 200, response.text
    assert response.json()[field] == expected
    [row] = audit_rows("AST-000001", "asset.updated")
    assert row.actor_user_id == user.id
    assert row.before_data == {field: before.isoformat() if hasattr(before, "isoformat") else before}
    assert row.after_data == {field: expected}
    assert response.json()["status"] == "available"  # editing never changes the status


def test_several_fields_in_one_edit_write_one_audit_row(client, laptops):
    response = edit(client, laptops, "ast-000001", name="Spare laptop", location="Store room", brand="DELL")

    assert response.status_code == 200
    [row] = audit_rows("AST-000001", "asset.updated")
    assert row.before_data == {"name": "Laptops: Dell Latitude 5440", "location": "Bangalore Floor 2", "brand": "Dell"}
    assert row.after_data == {"name": "Spare laptop", "location": "Store room", "brand": "DELL"}


def test_optional_fields_can_be_cleared_with_null(client, laptops):
    response = edit(client, laptops, "AST-000001", brand=None, location="   ", warranty_expiry=None)

    assert response.status_code == 200
    asset = stored("AST-000001")
    assert (asset.brand, asset.location, asset.warranty_expiry) == (None, None, None)


def test_sending_the_same_values_saves_nothing_and_writes_no_audit_row(client, laptops):
    before = stored("AST-000001")

    response = edit(client, laptops, "AST-000001", name="Laptops: Dell Latitude 5440", location=" Bangalore Floor 2 ")

    assert response.status_code == 200
    assert audit_rows("AST-000001", "asset.updated") == []
    assert stored("AST-000001").updated_at == before.updated_at


@pytest.mark.parametrize(
    "field, value, code",
    [
        ("name", None, "invalid_asset_name"),
        ("name", "   ", "invalid_asset_name"),
        ("name", "x" * 201, "invalid_asset_name"),
        ("model", "", "invalid_model"),
        ("serial_number", None, "invalid_serial_number"),
        ("serial_number", "s" * 101, "invalid_serial_number"),
        ("brand", "b" * 101, "invalid_brand"),
        ("location", "l" * 201, "invalid_location"),
    ],
)
def test_required_and_too_long_values_are_refused(client, laptops, field, value, code):
    before = stored("AST-000001")

    response = edit(client, laptops, "AST-000001", **{field: value})

    assert response.status_code == 422
    assert error_code(response) == code
    assert getattr(stored("AST-000001"), field) == getattr(before, field)


def test_warranty_before_the_purchase_date_is_refused(client, laptops):
    response = edit(client, laptops, "AST-000001", warranty_expiry="2019-11-10")

    assert response.status_code == 422
    assert error_code(response) == "invalid_warranty_expiry"
    assert stored("AST-000001").warranty_expiry.isoformat() == "2029-11-10"


# ---- Editing: serial numbers stay unique ----------------------------------------------------------
def test_serial_used_by_another_asset_is_refused_in_any_case(client, laptops):
    response = edit(client, laptops, "AST-000001", serial_number="dl-1002")

    assert response.status_code == 409
    assert error_code(response) == "serial_number_taken"
    assert stored("AST-000001").serial_number == "DL-1001"
    assert audit_rows("AST-000001", "asset.updated") == []


def test_changing_only_the_case_of_its_own_serial_is_allowed(client, laptops):
    response = edit(client, laptops, "AST-000001", serial_number="dl-1001")

    assert response.status_code == 200
    assert stored("AST-000001").serial_number == "dl-1001"


def test_database_index_still_blocks_a_duplicate_serial(db, laptops):
    asset = db.scalars(select(Asset).where(Asset.asset_code == "AST-000001")).one()
    asset.serial_number = "DL-1002"
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---- Editing: status and locked fields are refused --------------------------------------------------
@pytest.mark.parametrize(
    "body",
    [
        {"status": "available"},
        {"status": "retired"},
        {"category_id": 1},
        {"purchase_date": "2026-01-01"},
        {"cost": "1.00"},
        {"purchase_line_id": 1},
        {"asset_code": "AST-999999"},
        {"retire_reason": "x"},
        {"name": "Fine", "status": "assigned"},  # one bad field refuses the whole edit
    ],
)
def test_status_and_locked_fields_are_a_validation_error(client, laptops, body):
    before = stored("AST-000001")

    response = edit(client, laptops, "AST-000001", **body)

    assert response.status_code == 422
    assert error_code(response) == "validation_error"
    after = stored("AST-000001")
    assert (after.name, after.status, after.category_id, after.cost, after.purchase_date) == (
        before.name, before.status, before.category_id, before.cost, before.purchase_date,
    )
    assert audit_rows("AST-000001", "asset.updated") == []


@pytest.mark.parametrize("status", ["assigned", "under_maintenance", "damaged"])
def test_assets_in_other_statuses_can_still_be_edited(client, laptops, status):
    set_status("AST-000001", status)

    response = edit(client, laptops, "AST-000001", location="Chennai")

    assert response.status_code == 200
    assert response.json()["status"] == status


# ---- Retiring ------------------------------------------------------------------------------------
def test_retiring_an_available_asset_records_who_when_why_and_audits_it(client, manager, laptops):
    user, headers = manager

    response = retire(client, headers, "AST-000001", "  Screen cracked beyond repair  ")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "retired"
    assert body["retire_reason"] == "Screen cracked beyond repair"
    assert body["retired_by"] == {"id": user.id, "email": user.email}
    assert body["retired_at"]
    [row] = audit_rows("AST-000001", "asset.retired")
    assert row.actor_user_id == user.id
    assert row.before_data == {"status": "available"}
    assert row.after_data == {"status": "retired", "reason": "Screen cracked beyond repair"}


def test_a_damaged_asset_can_be_retired(client, laptops):
    set_status("AST-000002", "damaged")

    response = retire(client, laptops, "AST-000002")

    assert response.status_code == 200
    assert response.json()["status"] == "retired"
    assert audit_rows("AST-000002", "asset.retired")[0].before_data == {"status": "damaged"}


@pytest.mark.parametrize("status, hint", [("assigned", "Return it first."), ("under_maintenance", "Finish the repair first.")])
def test_assigned_or_under_maintenance_assets_cannot_be_retired(client, laptops, status, hint):
    set_status("AST-000001", status)

    response = retire(client, laptops, "AST-000001")

    assert response.status_code == 409
    body = response.json()["error"]
    assert body["code"] == "asset_not_retirable"
    assert body["details"] == {"status": status}
    assert hint in body["message"]
    asset = stored("AST-000001")
    assert (asset.status, asset.retired_at, asset.retire_reason) == (status, None, None)
    assert audit_rows("AST-000001", "asset.retired") == []


@pytest.mark.parametrize("reason", [None, "", "    "])
def test_a_reason_is_required(client, laptops, reason):
    response = retire(client, laptops, "AST-000001", reason)

    assert response.status_code == 422
    assert error_code(response) == "invalid_retire_reason"
    assert stored("AST-000001").status == "available"


def test_reason_up_to_500_characters(client, laptops):
    too_long = retire(client, laptops, "AST-000001", "r" * 501)
    exactly = retire(client, laptops, "AST-000002", "r" * 500)

    assert too_long.status_code == 422 and error_code(too_long) == "invalid_retire_reason"
    assert stored("AST-000001").status == "available"
    assert exactly.status_code == 200 and len(exactly.json()["retire_reason"]) == 500


def test_retire_needs_a_body_with_reason_only(client, laptops):
    missing = client.post(f"{ASSETS}/AST-000001/retire", headers=laptops)
    extra = client.post(f"{ASSETS}/AST-000001/retire", headers=laptops, json={"reason": "x", "status": "available"})

    assert missing.status_code == 422 and extra.status_code == 422
    assert stored("AST-000001").status == "available"


# ---- Done-check: a retired asset is final ------------------------------------------------------------
def test_retired_asset_shows_its_reason_in_history_and_cannot_be_edited_back_to_available(client, laptops):
    retire(client, laptops, "AST-000001", "Stolen from the Chennai office")
    history = client.get(f"{ASSETS}/AST-000001/history", headers=laptops).json()["items"]

    assert history[0]["action"] == "asset.retired"
    assert history[0]["after"]["reason"] == "Stolen from the Chennai office"

    back = edit(client, laptops, "AST-000001", status="available")
    assert back.status_code == 422 and error_code(back) == "validation_error"
    rename = edit(client, laptops, "AST-000001", name="Back in use")
    assert rename.status_code == 409 and error_code(rename) == "asset_retired"
    again = retire(client, laptops, "AST-000001", "Again")
    assert again.status_code == 409 and error_code(again) == "asset_retired"

    asset = stored("AST-000001")
    assert (asset.status, asset.name, asset.retire_reason) == ("retired", "Laptops: Dell Latitude 5440", "Stolen from the Chennai office")
    assert len(audit_rows("AST-000001", "asset.retired")) == 1


def test_history_shows_each_edit_and_the_retirement_newest_first(client, laptops):
    edit(client, laptops, "AST-000001", location="Chennai")
    edit(client, laptops, "AST-000001", serial_number="DL-1001-X")
    retire(client, laptops, "AST-000001", "End of life")

    actions = [e["action"] for e in client.get(f"{ASSETS}/AST-000001/history", headers=laptops).json()["items"]]

    assert actions == ["asset.retired", "asset.updated", "asset.updated", "asset.created"]


# ---- Nothing is saved when something fails ----------------------------------------------------------
@pytest.mark.parametrize("action", ["edit", "retire"])
def test_a_failing_audit_row_saves_nothing(client, laptops, monkeypatch, action):
    def broken_record(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr(audit_service, "record", broken_record)
    with pytest.raises(RuntimeError):
        if action == "edit":
            edit(client, laptops, "AST-000001", name="Changed", location="Chennai")
        else:
            retire(client, laptops, "AST-000001")

    asset = stored("AST-000001")
    assert (asset.name, asset.location, asset.status, asset.retire_reason) == (
        "Laptops: Dell Latitude 5440", "Bangalore Floor 2", "available", None,
    )
    assert [r.action for r in audit_rows("AST-000001")] == ["asset.created"]


def _retire_in_own_session(asset_code, user_id, reason, results, barrier):
    from app.core.errors import AppError
    from app.modules.assets import service
    from app.modules.users.models import User

    with SessionLocal() as session:
        actor = session.get(User, user_id)
        asset = service.get_asset(session, asset_code)
        barrier.wait()
        try:
            service.retire_asset(session, actor=actor, asset=asset, reason=reason)
            results.append(("ok", reason))
        except AppError as error:
            results.append(("error", error.code))


def test_two_people_retiring_at_the_same_moment_only_one_wins(manager, laptops):
    import threading

    user, _ = manager
    results: list = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_retire_in_own_session, args=("AST-000001", user.id, reason, results, barrier))
        for reason in ("Reason A", "Reason B")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(kind for kind, _ in results) == ["error", "ok"]
    assert ("error", "asset_retired") in results
    winner = next(value for kind, value in results if kind == "ok")
    assert stored("AST-000001").retire_reason == winner
    assert len(audit_rows("AST-000001", "asset.retired")) == 1


def test_database_keeps_retirement_details_empty_unless_retired(db, laptops):
    asset = db.scalars(select(Asset).where(Asset.asset_code == "AST-000001")).one()
    asset.retire_reason = "not really retired"
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---- Roles and unknown assets -------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_edit_and_retire(client, staff_headers, laptops, role):
    _, headers = staff_headers(role)
    assert edit(client, headers, "AST-000001", location="Chennai").status_code == 200
    assert retire(client, headers, "AST-000001").status_code == 200


def test_employee_role_cannot_edit_or_retire(client, staff_headers, laptops):
    _, headers = staff_headers("Employee")

    edited = edit(client, headers, "AST-000001", location="Chennai")
    retired = retire(client, headers, "AST-000001")

    assert edited.status_code == 403 and error_code(edited) == "forbidden"
    assert retired.status_code == 403 and error_code(retired) == "forbidden"
    asset = stored("AST-000001")
    assert (asset.location, asset.status) == ("Bangalore Floor 2", "available")


def test_edit_and_retire_need_login(client, laptops):
    assert client.patch(f"{ASSETS}/AST-000001", json={"location": "x"}).status_code == 401
    assert client.post(f"{ASSETS}/AST-000001/retire", json={"reason": "x"}).status_code == 401


@pytest.mark.parametrize("ref", ["AST-999999", "99999"])
def test_unknown_asset_gives_404(client, laptops, ref):
    assert error_code(edit(client, laptops, ref, location="x")) == "asset_not_found"
    assert error_code(retire(client, laptops, ref)) == "asset_not_found"
