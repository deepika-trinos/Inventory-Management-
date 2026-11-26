"""Employee self-service (Slice 6.4: MNT-08, PRD 4.1 / 4.2; owner's answers in decisions.md section 37,
decisions W1-W6 in section 38).

- GET /me/maintenance-requests (Employee only): the requests the login REPORTED, newest first, also after
  the asset was returned (O6); not requests staff created; not other employees' requests.
- Only Employee-safe fields: number, asset (ID, name, serial), problem, status, reported / started /
  completed / cancelled dates, cancel reason. Never priority, provider, repair notes, cost, staff e-mails
  or inspection details.
- Staff 403, no login 401; every staff maintenance endpoint answers 403 to an Employee; reading writes nothing.

Done-check (build plan): an Employee can follow their own request and cannot see anyone else's data."""

import pytest

from tests.test_asset_edit_retire import audit_rows
from tests.test_assign_asset import (  # noqa: F401  (pytest fixtures used by name)
    ASSETS,
    assign,
    laptops,
    people,
    today,
)
from tests.test_purchases_api import (  # noqa: F401  (pytest fixtures used by name)
    data,
    error_code,
    manager,
    staff_headers,
)
from tests.test_report_problem import (  # noqa: F401  (pytest fixtures used by name)
    MINE,
    asha_holds_one,
    asset_id,
    my_report,
    ravi_login,
    report,
)
from tests.test_repair_progress import REQUESTS, cancel, complete, start

ALLOWED_KEYS = {
    "request_number", "asset", "issue_description", "status", "reported_date", "started_date",
    "completion_date", "cancelled_date", "cancel_reason",
}


def mine(client, headers):
    return client.get(MINE, headers=headers)


def return_asset(client, headers, code):
    response = client.post(f"{ASSETS}/{code}/return", headers=headers, json={"inspection_outcome": "available"})
    assert response.status_code == 200, response.text


@pytest.fixture
def asha_reported(client, laptops, asha_holds_one):
    """Asha (EMP-001, Employee login) holds AST-000001 and reported MNT-000001 on it."""
    response = my_report(client, asha_holds_one, asset_id("AST-000001"), "Battery drains fast")
    assert response.status_code == 201, response.text
    return asha_holds_one


# ---- Following my own request (the done-check) ----------------------------------------------------------
def test_an_employee_follows_their_request_to_completion(client, laptops, asha_reported):
    first = mine(client, asha_reported).json()
    assert [(r["request_number"], r["status"]) for r in first] == [("MNT-000001", "reported")]
    assert first[0]["reported_date"] == today().isoformat()

    return_asset(client, laptops, "AST-000001")  # S1: returned before work starts
    start(client, laptops, "MNT-000001", service_provider="Dell Service Centre")
    complete(client, laptops, "MNT-000001", cost="1200.50")

    row = mine(client, asha_reported).json()[0]  # still theirs after the return (O6)
    assert row["status"] == "completed"
    assert row["started_date"] == today().isoformat()
    assert row["completion_date"] == today().isoformat()
    assert row["asset"] == {"asset_code": "AST-000001", "name": row["asset"]["name"], "serial_number": "DL-1001"}


def test_a_cancelled_request_shows_the_date_and_reason(client, laptops, asha_reported):
    cancel(client, laptops, "MNT-000001", reason="Fixed by restarting")

    row = mine(client, asha_reported).json()[0]
    assert (row["status"], row["cancelled_date"], row["cancel_reason"]) == (
        "cancelled", today().isoformat(), "Fixed by restarting",
    )


def test_newest_first(client, laptops, asha_reported):
    cancel(client, laptops, "MNT-000001", reason="Duplicate")
    my_report(client, asha_reported, asset_id("AST-000001"), "Fan noisy")

    assert [r["request_number"] for r in mine(client, asha_reported).json()] == ["MNT-000002", "MNT-000001"]


def test_no_requests_yet(client, laptops, asha_holds_one):
    assert mine(client, asha_holds_one).json() == []


# ---- Privacy (PRD 4.1) -------------------------------------------------------------------------------------
def test_only_employee_safe_fields_are_sent(client, laptops, asha_reported):
    return_asset(client, laptops, "AST-000001")
    client.patch(f"{REQUESTS}/MNT-000001", headers=laptops, json={"priority": "high"})
    start(client, laptops, "MNT-000001", service_provider="Dell Service Centre")
    complete(client, laptops, "MNT-000001", notes="Secret staff note", cost="999.00")
    client.post(f"{REQUESTS}/MNT-000001/inspect", headers=laptops, json={"inspection_outcome": "damaged", "condition_notes": "Hinge"})

    response = mine(client, asha_reported)
    row = response.json()[0]
    assert set(row) == ALLOWED_KEYS
    assert set(row["asset"]) == {"asset_code", "name", "serial_number"}
    for hidden in ("Secret staff note", "Dell Service Centre", "999", "high", "Hinge", "damaged", "@example.com"):
        assert hidden not in response.text


def test_other_employees_requests_are_not_shown(client, laptops, people, asha_reported, ravi_login):
    assign(client, laptops, "AST-000002", people["ravi"])
    assert my_report(client, ravi_login, asset_id("AST-000002"), "Ravi's problem").status_code == 201

    assert [r["request_number"] for r in mine(client, asha_reported).json()] == ["MNT-000001"]
    assert [r["request_number"] for r in mine(client, ravi_login).json()] == ["MNT-000002"]


def test_requests_staff_created_on_my_asset_are_not_shown(client, laptops, asha_holds_one):
    assert report(client, laptops, "AST-000001", "Staff noticed a crack").status_code == 201

    assert mine(client, asha_holds_one).json() == []


def test_staff_get_403_and_no_login_401(client, staff_headers):
    for role in ("Admin", "IT Manager"):
        _, headers = staff_headers(role)
        response = mine(client, headers)
        assert (response.status_code, error_code(response)) == (403, "forbidden")
    assert mine(client, {}).status_code == 401


def test_every_staff_maintenance_endpoint_refuses_an_employee(client, laptops, asha_reported):
    calls = [
        ("get", REQUESTS, None),
        ("get", f"{REQUESTS}/MNT-000001", None),
        ("post", f"{REQUESTS}/MNT-000001/start", {}),
        ("post", f"{REQUESTS}/MNT-000001/complete", {"repair_notes": "x"}),
        ("post", f"{REQUESTS}/MNT-000001/cancel", {"reason": "x"}),
        ("post", f"{REQUESTS}/MNT-000001/inspect", {"inspection_outcome": "available"}),
        ("patch", f"{REQUESTS}/MNT-000001", {"priority": "high"}),
        ("get", f"{ASSETS}/AST-000001/maintenance-requests", None),
        ("post", f"{ASSETS}/AST-000001/maintenance-requests", {"issue_description": "x"}),
    ]
    for method, url, body in calls:
        response = getattr(client, method)(url, headers=asha_reported, **({"json": body} if body is not None else {}))
        assert response.status_code == 403, (method, url, response.status_code)


def test_reading_writes_nothing(client, laptops, asha_reported):
    before = len(audit_rows("AST-000001"))
    mine(client, asha_reported)
    mine(client, asha_reported)
    assert len(audit_rows("AST-000001")) == before
