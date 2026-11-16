"""Receiving one-by-one items (Slice 3.2: PUR-05, PUR-06, AST-01, AST-02, AST-06, BR-01,
BR-07, BR-08, BR-13; decisions Q2, Q3, P4-P6, B14, B55-B65) and reading one asset."""

import threading
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.modules.assets.models import Asset
from app.modules.audit.models import AuditLog
from app.modules.categories import service as categories_service
from app.modules.purchases import service
from app.modules.purchases.models import Purchase, PurchaseLine
from app.modules.purchases.service import _today
from app.modules.vendors import service as vendors_service
from app.modules.vendors.models import Vendor
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
    stock_tables_snapshot,
)

ASSETS = "/api/v1/assets"
CATEGORIES = "/api/v1/categories"


def unit(serial, model="Latitude 5440", **extra):
    return {"serial_number": serial, "model": model, **extra}


def laptops_only(client, headers, data, quantity=3, **overrides):
    """A draft with ONE one-by-one line (laptops), returned as JSON."""
    response = create(client, headers, data, lines=[laptop_line(data["laptops"], quantity=quantity)], **overrides)
    assert response.status_code == 201, response.text
    return response.json()


def receipt(purchase, *per_line, received_date=None):
    """Request body: per_line[i] is the list of units for line i (its length = quantity received)."""
    return {
        "received_date": (received_date or _today()).isoformat(),
        "lines": [
            {"line_id": line["id"], "received_quantity": len(units), "units": units}
            for line, units in zip(purchase["lines"], per_line, strict=True)
        ],
    }


def receive(client, headers, purchase, body):
    return client.post(f"{PURCHASES}/{purchase['id']}/receive", headers=headers, json=body)


def all_assets() -> list[Asset]:
    with SessionLocal() as fresh:
        return list(fresh.scalars(select(Asset).order_by(Asset.id)).all())


def in_database(purchase_id: int) -> Purchase:
    with SessionLocal() as fresh:
        purchase = fresh.get(Purchase, purchase_id)
        fresh.expunge_all()
        return purchase


def line_received(line_id: int):
    with SessionLocal() as fresh:
        return fresh.get(PurchaseLine, line_id).received_quantity


def assert_nothing_saved(purchase):
    """The receipt was refused: still a draft, no quantities, no assets, no audit rows."""
    saved = in_database(purchase["id"])
    assert saved.status == "draft" and saved.received_date is None
    assert all(line_received(line["id"]) is None for line in purchase["lines"])
    assert all_assets() == []
    assert audit_for(purchase["id"], "purchase.received") == []
    with SessionLocal() as fresh:
        assert fresh.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "asset.created")) == 0


# ---- Done-check: receiving 3 laptops creates 3 assets with unique IDs ------------------------
def test_receiving_three_laptops_creates_three_available_assets(client, manager, data):
    user, headers = manager
    purchase = laptops_only(client, headers, data, quantity=3)
    stock_before = stock_tables_snapshot()

    response = receive(
        client, headers, purchase,
        receipt(purchase, [
            unit("SN-1001", brand="Dell", warranty_expiry="2029-11-30", location="Bengaluru office, IT store"),
            unit("SN-1002", brand="Dell"),
            unit("SN-1003"),
        ]),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "received" and body["received_date"] == _today().isoformat()
    [line] = body["lines"]
    assert line["received_quantity"] == 3
    assert [a["asset_code"] for a in line["assets"]] == ["AST-000001", "AST-000002", "AST-000003"]
    assert [a["serial_number"] for a in line["assets"]] == ["SN-1001", "SN-1002", "SN-1003"]

    assets = all_assets()
    assert len({a.asset_code for a in assets}) == 3
    for asset in assets:
        assert asset.status == "available"
        assert asset.purchase_line_id == line["id"]
        assert asset.category_id == data["laptops"]
        assert asset.name == "Laptops: Dell Latitude 5440"  # the line's description (B57)
        assert asset.model == "Latitude 5440"
        assert str(asset.cost) == "85000.00"  # the line's unit cost (AST-02)
        assert asset.purchase_date == _today()
        assert asset.created_by_user_id == user.id
    first = assets[0]
    assert first.brand == "Dell" and first.location == "Bengaluru office, IT store"
    assert first.warranty_expiry.isoformat() == "2029-11-30"
    assert assets[2].brand is None and assets[2].location is None and assets[2].warranty_expiry is None
    # One-by-one items never touch bulk stock (BR-08).
    assert stock_tables_snapshot() == stock_before


def test_received_purchase_shows_its_assets_and_is_final(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=1)
    receive(client, headers, purchase, receipt(purchase, [unit("SN-1")]))

    fetched = client.get(f"{PURCHASES}/{purchase['id']}", headers=headers).json()
    assert fetched["status"] == "received"
    assert fetched["lines"][0]["assets"][0]["asset_code"] == "AST-000001"
    # Final (P6): no edit, cancel or second receipt.
    assert error_code(client.patch(f"{PURCHASES}/{purchase['id']}", headers=headers, json={"notes": "x"})) == "purchase_not_draft"
    assert error_code(client.post(f"{PURCHASES}/{purchase['id']}/cancel", headers=headers)) == "purchase_not_draft"
    again = receive(client, headers, purchase, receipt(purchase, [unit("SN-2")]))
    assert again.status_code == 409 and error_code(again) == "purchase_not_draft"
    assert len(all_assets()) == 1


def test_draft_purchase_lines_have_no_assets(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data)
    assert purchase["lines"][0]["assets"] == [] and purchase["lines"][0]["received_quantity"] is None


# ---- Serial numbers: unique across all assets, any case (AST-06, P5) --------------------------
@pytest.mark.parametrize("serial", ["SN-1001", "sn-1001", "  Sn-1001  "])
def test_serial_used_by_an_existing_asset_blocks_the_whole_receipt(client, manager, data, serial):
    _, headers = manager
    first = laptops_only(client, headers, data, quantity=1, reference_number="FIRST")
    assert receive(client, headers, first, receipt(first, [unit("SN-1001")])).status_code == 200
    second = laptops_only(client, headers, data, quantity=3, reference_number="SECOND")

    response = receive(client, headers, second, receipt(second, [unit("SN-2001"), unit(serial), unit("SN-2003")]))

    assert response.status_code == 409
    assert error_code(response) == "serial_number_taken"
    assert response.json()["error"]["details"] == {"line": 1, "unit": 2}
    assert in_database(second["id"]).status == "draft"
    assert [a.serial_number for a in all_assets()] == ["SN-1001"]  # nothing from the second receipt
    assert audit_for(second["id"], "purchase.received") == []


def test_same_serial_twice_in_one_receipt_is_blocked_in_any_case(client, manager, data):
    _, headers = manager
    response = create(
        client, headers, data,
        lines=[laptop_line(data["laptops"], quantity=2), laptop_line(data["laptops"], quantity=1, description="Laptops: spare")],
    )
    purchase = response.json()

    refused = receive(client, headers, purchase, receipt(purchase, [unit("ABC-1"), unit("ABC-2")], [unit("abc-1")]))

    assert refused.status_code == 409
    assert error_code(refused) == "serial_number_duplicate"
    assert refused.json()["error"]["details"] == {"line": 2, "unit": 1, "other_line": 1, "other_unit": 1}
    assert_nothing_saved(purchase)


def test_database_index_blocks_duplicate_serials_even_without_the_service(db, data, make_user):
    user, _ = make_user("IT Manager")
    db.add(Asset(name="A", category_id=data["laptops"], model="M", serial_number="DUP-1", created_by_user_id=user.id))
    db.commit()
    db.add(Asset(name="B", category_id=data["laptops"], model="M", serial_number="dup-1", created_by_user_id=user.id))
    with pytest.raises(IntegrityError, match="uq_assets_serial_number_lower"):
        db.commit()
    db.rollback()


# ---- Quantities (P4, B58) ---------------------------------------------------------------------
def test_fewer_than_ordered_is_allowed_and_closes_the_line(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=3)

    response = receive(client, headers, purchase, receipt(purchase, [unit("SN-1"), unit("SN-2")]))

    assert response.status_code == 200, response.text
    assert response.json()["lines"][0]["received_quantity"] == 2
    assert len(all_assets()) == 2
    assert response.json()["status"] == "received"  # the line is closed: the third never arrives


def test_a_line_can_be_received_as_zero_when_another_line_arrives(client, manager, data):
    _, headers = manager
    purchase = create(
        client, headers, data,
        lines=[laptop_line(data["laptops"], quantity=2), laptop_line(data["laptops"], quantity=1, description="Monitors")],
    ).json()

    response = receive(client, headers, purchase, receipt(purchase, [], [unit("MON-1", model="P2422H")]))

    assert response.status_code == 200, response.text
    assert [line["received_quantity"] for line in response.json()["lines"]] == [0, 1]
    assert [a.name for a in all_assets()] == ["Monitors"]


def test_nothing_received_at_all_is_rejected(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data)

    response = receive(client, headers, purchase, receipt(purchase, []))

    assert response.status_code == 422 and error_code(response) == "nothing_received"
    assert_nothing_saved(purchase)


def test_more_than_ordered_is_rejected(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=2)

    response = receive(client, headers, purchase, receipt(purchase, [unit("A"), unit("B"), unit("C")]))

    assert response.status_code == 422
    assert error_code(response) == "received_quantity_too_high"
    assert response.json()["error"]["details"] == {"line": 1}
    assert_nothing_saved(purchase)


def test_units_must_match_the_received_quantity(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=3)
    body = receipt(purchase, [unit("A"), unit("B")])
    body["lines"][0]["received_quantity"] = 3  # says 3, sends 2

    response = receive(client, headers, purchase, body)

    assert response.status_code == 422 and error_code(response) == "unit_count_mismatch"
    assert_nothing_saved(purchase)


def test_negative_received_quantity_is_rejected(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data)
    body = receipt(purchase, [])
    body["lines"][0]["received_quantity"] = -1

    assert receive(client, headers, purchase, body).status_code == 422
    assert_nothing_saved(purchase)


def test_one_receipt_creates_at_most_1000_assets(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=1001)

    response = receive(client, headers, purchase, receipt(purchase, [unit(f"S-{n}") for n in range(1001)]))

    assert response.status_code == 422
    assert_nothing_saved(purchase)


# ---- Every line once (B55) --------------------------------------------------------------------
def test_every_line_must_be_sent_exactly_once(client, manager, data):
    _, headers = manager
    purchase = create(
        client, headers, data,
        lines=[laptop_line(data["laptops"], quantity=1), laptop_line(data["laptops"], quantity=1, description="Second")],
    ).json()
    full = receipt(purchase, [unit("A")], [unit("B")])

    missing = {**full, "lines": full["lines"][:1]}
    twice = {**full, "lines": [full["lines"][0], full["lines"][0], full["lines"][1]]}
    foreign = {**full, "lines": [*full["lines"], {"line_id": 999_999, "received_quantity": 0, "units": []}]}

    assert error_code(receive(client, headers, purchase, missing)) == "receipt_line_missing"
    assert error_code(receive(client, headers, purchase, twice)) == "invalid_receipt_line"
    assert error_code(receive(client, headers, purchase, foreign)) == "invalid_receipt_line"
    assert_nothing_saved(purchase)


# ---- Unit details (P5, B57) --------------------------------------------------------------------
@pytest.mark.parametrize(
    ("bad_unit", "code"),
    [
        ({"serial_number": "   ", "model": "M"}, "invalid_serial_number"),
        ({"serial_number": "S-1", "model": ""}, "invalid_model"),
        ({"serial_number": "S-1", "model": "  "}, "invalid_model"),
    ],
)
def test_missing_serial_or_model_is_rejected_with_its_place(client, manager, data, bad_unit, code):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=2)

    response = receive(client, headers, purchase, receipt(purchase, [unit("OK-1"), bad_unit]))

    assert response.status_code == 422 and error_code(response) == code
    assert response.json()["error"]["details"] == {"line": 1, "unit": 2}
    assert_nothing_saved(purchase)


@pytest.mark.parametrize("missing", ["serial_number", "model"])
def test_serial_and_model_fields_are_required(client, manager, data, missing):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=1)
    one = unit("S-1")
    del one[missing]

    response = receive(client, headers, purchase, receipt(purchase, [one]))

    assert response.status_code == 422 and error_code(response) == "validation_error"
    assert_nothing_saved(purchase)


def test_unit_text_is_trimmed_and_name_can_be_changed(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=2)

    response = receive(
        client, headers, purchase,
        receipt(purchase, [
            unit("  SN-9  ", model=" Latitude ", name="  Asha's laptop ", brand="  ", location=" Floor 2 "),
            unit("SN-10", name="   "),
        ]),
    )

    assert response.status_code == 200, response.text
    first, second = all_assets()
    assert (first.serial_number, first.model, first.name) == ("SN-9", "Latitude", "Asha's laptop")
    assert first.brand is None and first.location == "Floor 2"
    assert second.name == "Laptops: Dell Latitude 5440"  # empty name = the line's description


def test_unknown_unit_fields_are_refused(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=1)

    for field, value in [("status", "assigned"), ("asset_code", "AST-999999"), ("cost", "1.00")]:
        response = receive(client, headers, purchase, receipt(purchase, [unit("S-1", **{field: value})]))
        assert response.status_code == 422, field
    assert_nothing_saved(purchase)


# ---- Dates (B58) ------------------------------------------------------------------------------
def test_received_date_rules(client, manager, data):
    _, headers = manager
    purchase_date = _today() - timedelta(days=10)
    purchase = laptops_only(client, headers, data, quantity=1, purchase_date=purchase_date.isoformat())

    future = receive(client, headers, purchase, receipt(purchase, [unit("S-1")], received_date=_today() + timedelta(days=1)))
    early = receive(client, headers, purchase, receipt(purchase, [unit("S-1")], received_date=purchase_date - timedelta(days=1)))

    assert error_code(future) == "received_date_in_future"
    assert error_code(early) == "received_date_before_purchase"
    assert_nothing_saved(purchase)

    same_day = receive(client, headers, purchase, receipt(purchase, [unit("S-1")], received_date=purchase_date))
    assert same_day.status_code == 200, same_day.text
    assert same_day.json()["received_date"] == purchase_date.isoformat()


# ---- What can be received ---------------------------------------------------------------------
def test_cancelled_purchase_cannot_be_received(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data)
    client.post(f"{PURCHASES}/{purchase['id']}/cancel", headers=headers)

    response = receive(client, headers, purchase, receipt(purchase, [unit("S-1")]))

    assert response.status_code == 409 and error_code(response) == "purchase_not_draft"
    assert all_assets() == []


def test_draft_can_be_received_after_its_vendor_and_category_were_deactivated(client, manager, data, db):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=1)
    vendors_service.set_active(db, actor=None, vendor=db.get(Vendor, data["acme"]), active=False)
    categories_service.set_active(
        db, actor=None, category=categories_service.get_category(db, data["laptops"]), active=False
    )

    response = receive(client, headers, purchase, receipt(purchase, [unit("S-1")]))

    assert response.status_code == 200, response.text  # B59: the goods have arrived
    assert all_assets()[0].category_id == data["laptops"]


def test_unknown_purchase_is_404(client, manager):
    _, headers = manager
    response = client.post(
        f"{PURCHASES}/999999/receive", headers=headers, json={"received_date": _today().isoformat(), "lines": []}
    )
    assert response.status_code == 404 and error_code(response) == "purchase_not_found"


# ---- Category lock (B14, B63) -------------------------------------------------------------------
def test_category_with_assets_can_no_longer_switch_tracking_type(client, manager, data, db, make_user):
    _, headers = manager
    user, _ = make_user("IT Manager")
    # A category used ONLY by an asset (no purchase line, like manual entry in Slice 4.5).
    monitors = categories_service.create_category(db, name="Monitors", tracking_type="serialized")
    db.add(Asset(name="Old monitor", category_id=monitors.id, model="P2422H", serial_number="MON-OLD",
                 created_by_user_id=user.id))
    db.commit()

    locked = client.patch(f"{CATEGORIES}/{monitors.id}", headers=headers, json={"tracking_type": "bulk"})

    assert locked.status_code == 409 and error_code(locked) == "tracking_type_locked"


def test_retired_asset_still_locks_its_category(client, manager, db, make_user):
    _, headers = manager
    user, _ = make_user("IT Manager")
    cameras = categories_service.create_category(db, name="Cameras", tracking_type="serialized")
    db.add(Asset(name="Cam", category_id=cameras.id, model="X", serial_number="CAM-1", status="retired",
                 created_by_user_id=user.id))
    db.commit()

    locked = client.patch(f"{CATEGORIES}/{cameras.id}", headers=headers, json={"tracking_type": "bulk"})
    assert error_code(locked) == "tracking_type_locked"


# ---- Audit (BR-13) ----------------------------------------------------------------------------
def test_receipt_writes_purchase_received_and_one_asset_created_per_asset(client, manager, data):
    user, headers = manager
    purchase = laptops_only(client, headers, data, quantity=2)

    receive(client, headers, purchase, receipt(purchase, [unit("SN-A", brand="Dell"), unit("SN-B")]))

    [row] = audit_for(purchase["id"], "purchase.received")
    assert row.actor_user_id == user.id
    assert row.before_data["status"] == "draft" and row.before_data["received_date"] is None
    assert row.after_data["status"] == "received" and row.after_data["received_date"] == _today().isoformat()
    assert row.after_data["lines"][0]["received_quantity"] == 2
    assert row.after_data["lines"][0]["asset_codes"] == ["AST-000001", "AST-000002"]

    with SessionLocal() as fresh:
        rows = fresh.scalars(select(AuditLog).where(AuditLog.action == "asset.created").order_by(AuditLog.id)).all()
    assert [r.entity_type for r in rows] == ["assets", "assets"]
    assert [r.actor_user_id for r in rows] == [user.id, user.id]
    assert all(r.before_data is None for r in rows)
    assert [r.after_data["asset_code"] for r in rows] == ["AST-000001", "AST-000002"]
    assert rows[0].after_data["serial_number"] == "SN-A" and rows[0].after_data["brand"] == "Dell"
    assert rows[0].after_data["status"] == "available"
    assert rows[0].after_data["purchase_number"] == purchase["purchase_number"]
    assert rows[0].after_data["cost"] == "85000.00"


def test_forced_error_mid_receipt_saves_nothing(db, data, make_user, monkeypatch):
    """The audit write for the SECOND asset fails: the purchase, the quantities, the
    first asset and every audit row must all be rolled back."""
    from app.modules.audit import service as audit

    user, _ = make_user("IT Manager")
    purchase = service.create_purchase(
        db,
        data={"vendor_id": data["acme"], "reference_number": "R-1", "purchase_date": _today(),
              "lines": [laptop_line(data["laptops"], quantity=2)]},
        actor=user,
    )
    real_record = audit.record
    calls = {"asset.created": 0}

    def failing_record(*args, **kwargs):
        if kwargs.get("action") == "asset.created":
            calls["asset.created"] += 1
            if calls["asset.created"] == 2:
                raise RuntimeError("disk full")
        return real_record(*args, **kwargs)

    monkeypatch.setattr(audit, "record", failing_record)
    line_id = purchase.lines[0].id
    with pytest.raises(RuntimeError):
        service.receive_purchase(
            db, actor=user, purchase=purchase,
            data={"received_date": _today(), "lines": [
                {"line_id": line_id, "received_quantity": 2, "units": [unit("S-1"), unit("S-2")]},
            ]},
        )

    assert calls["asset.created"] == 2  # the first asset really was written before the failure
    with SessionLocal() as fresh:
        saved = fresh.get(Purchase, purchase.id)
        assert saved.status == "draft" and saved.received_date is None
        assert fresh.get(PurchaseLine, line_id).received_quantity is None
        assert fresh.scalars(select(Asset)).all() == []
        assert fresh.scalars(
            select(AuditLog).where(AuditLog.action.in_(["purchase.received", "asset.created"]))
        ).all() == []


# ---- Two receipts at the same moment ------------------------------------------------------------
def _receive_in_own_session(purchase_id, user_id, units, results, barrier):
    with SessionLocal() as session:
        from app.modules.users.models import User

        actor = session.get(User, user_id)
        purchase = service.get_purchase(session, purchase_id)
        barrier.wait()
        try:
            saved = service.receive_purchase(
                session, actor=actor, purchase=purchase,
                data={"received_date": _today(), "lines": [
                    {"line_id": purchase.lines[0].id, "received_quantity": len(units), "units": units},
                ]},
            )
            results.append(("ok", [a.asset_code for a in saved.lines[0].assets]))
        except AppError as error:
            results.append(("error", error.code))


def _two_drafts(db, data, user, quantity):
    drafts = []
    for ref in ("PAR-1", "PAR-2"):
        drafts.append(
            service.create_purchase(
                db,
                data={"vendor_id": data["acme"], "reference_number": ref, "purchase_date": _today(),
                      "lines": [laptop_line(data["laptops"], quantity=quantity)]},
                actor=user,
            ).id
        )
    return drafts


def test_asset_ids_stay_unique_when_two_receipts_run_at_the_same_time(db, data, make_user):
    user, _ = make_user("IT Manager")
    first, second = _two_drafts(db, data, user, quantity=5)
    results: list = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_receive_in_own_session,
                         args=(first, user.id, [unit(f"A-{n}") for n in range(5)], results, barrier)),
        threading.Thread(target=_receive_in_own_session,
                         args=(second, user.id, [unit(f"B-{n}") for n in range(5)], results, barrier)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert [status for status, _ in results] == ["ok", "ok"]
    codes = [code for _, batch in results for code in batch]
    assert len(codes) == 10 and len(set(codes)) == 10
    with SessionLocal() as fresh:
        assert sorted(fresh.scalars(select(Asset.asset_code)).all()) == [f"AST-{n:06d}" for n in range(1, 11)]


def test_same_serial_in_two_receipts_at_the_same_time_only_one_wins(db, data, make_user):
    user, _ = make_user("IT Manager")
    first, second = _two_drafts(db, data, user, quantity=1)
    results: list = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_receive_in_own_session, args=(pid, user.id, [unit("SAME-1")], results, barrier))
        for pid in (first, second)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert sorted(status for status, _ in results) == ["error", "ok"]
    assert [code for status, code in results if status == "error"] == ["serial_number_taken"]
    with SessionLocal() as fresh:
        assert fresh.scalar(select(func.count()).select_from(Asset)) == 1
        statuses = sorted(fresh.scalars(select(Purchase.status)).all())
    assert statuses == ["draft", "received"]  # the losing receipt saved nothing


# ---- Roles (P6) ---------------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_receive_and_read_assets(client, staff_headers, data, role):
    _, headers = staff_headers(role)
    purchase = laptops_only(client, headers, data, quantity=1)

    assert receive(client, headers, purchase, receipt(purchase, [unit("S-1")])).status_code == 200
    assert client.get(f"{ASSETS}/AST-000001", headers=headers).status_code == 200


def test_employee_gets_403_on_receive_and_assets(client, staff_headers, manager, data):
    _, manager_headers = manager
    purchase = laptops_only(client, manager_headers, data, quantity=1)
    _, employee = staff_headers("Employee")

    refused = receive(client, employee, purchase, receipt(purchase, [unit("S-1")]))

    assert refused.status_code == 403 and error_code(refused) == "forbidden"
    assert client.get(f"{ASSETS}/1", headers=employee).status_code == 403
    assert_nothing_saved(purchase)


def test_receive_and_assets_need_login(client, manager, data):
    _, headers = manager
    purchase = laptops_only(client, headers, data, quantity=1)

    assert receive(client, {}, purchase, receipt(purchase, [unit("S-1")])).status_code == 401
    assert client.get(f"{ASSETS}/1").status_code == 401
    assert_nothing_saved(purchase)


# ---- Reading one asset --------------------------------------------------------------------------
def test_get_one_asset_by_id_or_asset_id(client, manager, data):
    user, headers = manager
    purchase = laptops_only(client, headers, data, quantity=2)
    receive(client, headers, purchase, receipt(purchase, [unit("SN-1"), unit("SN-2", brand="Dell")]))

    by_code = client.get(f"{ASSETS}/ast-000002", headers=headers)
    by_id = client.get(f"{ASSETS}/2", headers=headers)

    assert by_code.status_code == 200 and by_code.json() == by_id.json()
    body = by_code.json()
    assert body["asset_code"] == "AST-000002" and body["serial_number"] == "SN-2" and body["brand"] == "Dell"
    assert body["status"] == "available" and body["cost"] == "85000.00"
    assert body["category"]["name"] == "Laptops"
    assert body["purchase"] == {
        "purchase_id": purchase["id"],
        "purchase_number": purchase["purchase_number"],
        "purchase_line_id": purchase["lines"][0]["id"],
        "vendor": "Acme IT Supplies",
        "reference_number": "INV-2026-0042",
    }
    assert body["created_by"] == {"id": user.id, "email": user.email}


@pytest.mark.parametrize("ref", ["999", "AST-999999", "abc", "PUR-000001"])
def test_unknown_asset_is_404(client, manager, ref):
    _, headers = manager
    response = client.get(f"{ASSETS}/{ref}", headers=headers)
    assert response.status_code == 404 and error_code(response) == "asset_not_found"


def test_there_is_no_asset_delete_or_list_yet(client, manager):
    _, headers = manager
    assert client.delete(f"{ASSETS}/1", headers=headers).status_code == 405
    assert client.get(ASSETS, headers=headers).status_code in (404, 405)  # the register is Slice 4.1


# ---- Database rules -----------------------------------------------------------------------------
def test_database_rejects_unknown_status_blank_serial_and_negative_cost(db, data, make_user):
    user, _ = make_user("IT Manager")
    base = {"name": "A", "category_id": data["laptops"], "model": "M", "created_by_user_id": user.id}
    for bad in ({"serial_number": "X-1", "status": "lost"}, {"serial_number": "   "}, {"serial_number": "X-2", "cost": -1}):
        db.add(Asset(**base, **bad))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    assert db.execute(text("SELECT count(*) FROM assets")).scalar_one() == 0


# ---- B61: warranty expiry is optional, but not before the purchase date -----------------------
def test_warranty_expiry_before_the_purchase_date_is_rejected(client, manager, data):
    _, headers = manager
    bought = _today() - timedelta(days=10)
    purchase = laptops_only(client, headers, data, quantity=2, purchase_date=bought.isoformat())
    too_early = (bought - timedelta(days=1)).isoformat()

    response = receive(
        client, headers, purchase,
        receipt(purchase, [unit("S-1"), unit("S-2", warranty_expiry=too_early)]),
    )

    assert response.status_code == 422 and error_code(response) == "invalid_warranty_expiry"
    assert response.json()["error"]["details"] == {"line": 1, "unit": 2}
    assert_nothing_saved(purchase)


def test_warranty_expiry_on_the_purchase_date_or_empty_is_fine(client, manager, data):
    _, headers = manager
    bought = _today() - timedelta(days=10)
    purchase = laptops_only(client, headers, data, quantity=2, purchase_date=bought.isoformat())

    response = receive(
        client, headers, purchase,
        receipt(purchase, [unit("S-1", warranty_expiry=bought.isoformat()), unit("S-2")]),
    )

    assert response.status_code == 200, response.text
    assert [a.warranty_expiry for a in all_assets()] == [bought, None]
