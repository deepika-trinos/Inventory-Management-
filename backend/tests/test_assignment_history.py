"""Assignment history and overdue returns (Slice 5.3: ASN-07, ASN-08, EMP-04; owner's answers N2,
N7, N8, N10-N13; decisions in decisions.md sections 29 and 30).

- GET /employees/{id}/assignments: current assets and past assignments (Admin, IT Manager).
- GET /assignments/overdue: expected return before today (company timezone), not returned.
- GET /me/assignments: the logged-in Employee's own records only, without condition notes or staff
  e-mails; Admin and IT Manager get 403.
- Read-only: nothing changes and no audit row is written.

Done-check (build plan): an employee's page shows a returned laptop in history, and an overdue item
appears in the overdue list."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.modules.assignments import service as assignments_service
from app.modules.audit.models import AuditLog
from tests.conftest import auth_header
from tests.test_assign_asset import (  # noqa: F401  (pytest fixtures used by name)
    ASSETS,
    EMPLOYEES,
    assign,
    assignments,
    created_days_ago,
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
from tests.test_return_asset import give_back

OVERDUE = "/api/v1/assignments/overdue"
MINE = "/api/v1/me/assignments"


def days(n: int) -> str:
    return (today() + timedelta(days=n)).isoformat()


@pytest.fixture
def scene(client, laptops, people):
    """Both laptops added 20 days ago.
    - AST-000001: Asha, assigned 15 days ago, expected back 10 days ago, returned 8 days ago as
      Available ("Minor scratches"); then Ravi, assigned 5 days ago, expected back 2 days ago:
      OVERDUE by 2 days.
    - AST-000002: Asha, assigned 4 days ago, expected back today: not overdue yet."""
    for code in ("AST-000001", "AST-000002"):
        created_days_ago(code, 20)
    h = laptops
    assert assign(client, h, "AST-000001", people["asha"], assignment_date=days(-15), expected_return_date=days(-10)).status_code == 200
    assert give_back(client, h, "AST-000001", "available", return_date=days(-8), condition_notes="Minor scratches").status_code == 200
    assert assign(client, h, "AST-000001", people["ravi"], assignment_date=days(-5), expected_return_date=days(-2)).status_code == 200
    assert assign(client, h, "AST-000002", people["asha"], assignment_date=days(-4), expected_return_date=days(0)).status_code == 200
    return h


def audit_count() -> int:
    with SessionLocal() as s:
        return s.scalar(select(func.count()).select_from(AuditLog))


# ---- Employee page (EMP-04, ASN-07) -------------------------------------------------------------------
def test_employee_page_shows_current_assets_and_a_returned_laptop_in_history(client, scene, people):
    response = client.get(f"{EMPLOYEES}/{people['asha']}/assignments", headers=scene)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["employee"]["employee_code"] == "EMP-001"
    [current] = body["current"]
    assert (current["asset"]["asset_code"], current["is_open"], current["is_overdue"]) == ("AST-000002", True, False)
    [past] = body["past"]
    assert past["asset"]["asset_code"] == "AST-000001"
    assert (past["assignment_date"], past["expected_return_date"], past["return_date"]) == (days(-15), days(-10), days(-8))
    assert (past["return_outcome"], past["condition_notes"], past["is_open"], past["is_overdue"]) == (
        "available", "Minor scratches", False, False,
    )
    assert past["assigned_by"]["email"] and past["returned_by"]["email"] and past["returned_at"]
    assert past["asset"]["status"] == "assigned"  # the asset's status NOW (with Ravi)


def test_old_assignments_are_kept_unchanged_after_a_new_one(client, scene, people):
    """ASN-07: assign, return, assign again: both rows kept; the first keeps its own details."""
    rows = assignments("AST-000001")
    assert [(r.employee_id, r.return_outcome) for r in rows] == [(people["asha"], "available"), (people["ravi"], None)]
    assert rows[0].assignment_date == today() - timedelta(days=15)


def test_past_assignments_are_newest_return_first(client, scene, people):
    assert assign(client, scene, "AST-000002", people["asha"]).status_code == 409  # still held
    give_back(client, scene, "AST-000002", "available", return_date=days(-1))

    past = client.get(f"{EMPLOYEES}/{people['asha']}/assignments", headers=scene).json()["past"]

    assert [p["asset"]["asset_code"] for p in past] == ["AST-000002", "AST-000001"]


def test_an_employee_with_nothing_has_empty_lists(client, scene, people):
    body = client.get(f"{EMPLOYEES}/{people['old']}/assignments", headers=scene).json()
    assert (body["current"], body["past"]) == ([], [])
    assert body["employee"]["status"] == "inactive"  # inactive employees can be viewed


def test_unknown_employee_gives_404(client, scene):
    response = client.get(f"{EMPLOYEES}/99999/assignments", headers=scene)
    assert response.status_code == 404
    assert error_code(response) == "employee_not_found"


# ---- Overdue (ASN-08, N7) -----------------------------------------------------------------------------------
def test_an_overdue_item_appears_in_the_overdue_list(client, scene, people):
    response = client.get(OVERDUE, headers=scene)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    [row] = body["items"]
    assert (row["asset"]["asset_code"], row["employee"]["employee_code"]) == ("AST-000001", "EMP-002")
    assert (row["expected_return_date"], row["is_overdue"], row["days_overdue"]) == (days(-2), True, 2)


def test_due_today_is_not_overdue_and_becomes_overdue_tomorrow(scene, db):
    from app.modules.assignments.models import Assignment

    a = db.scalars(select(Assignment).where(Assignment.expected_return_date == today())).one()
    assert assignments_service.days_overdue(a, today()) == 0
    assert assignments_service.days_overdue(a, today() + timedelta(days=1)) == 1


def test_no_expected_return_date_is_never_overdue(client, scene, people, db):
    from app.modules.assignments.models import Assignment

    give_back(client, scene, "AST-000002", "available")
    assign(client, scene, "AST-000002", people["asha"])  # no expected return date
    a = db.scalars(select(Assignment).where(Assignment.returned_at.is_(None), Assignment.expected_return_date.is_(None))).one()
    assert assignments_service.days_overdue(a, today() + timedelta(days=365)) == 0
    assert client.get(OVERDUE, headers=scene).json()["total"] == 1


def test_returning_an_overdue_asset_takes_it_off_the_list(client, scene, people):
    assert give_back(client, scene, "AST-000001", "available").status_code == 200

    assert client.get(OVERDUE, headers=scene).json() == {"items": [], "total": 0, "page": 1, "page_size": 20}
    past = client.get(f"{EMPLOYEES}/{people['ravi']}/assignments", headers=scene).json()["past"]
    assert past[0]["is_overdue"] is False and past[0]["days_overdue"] == 0


def test_overdue_uses_the_company_timezone(client, scene, monkeypatch):
    """N7: "today" is today in the company timezone (Q11), the same helper as every other date rule."""
    monkeypatch.setattr(assignments_service, "_today", lambda: today() - timedelta(days=3))
    assert client.get(OVERDUE, headers=scene).json()["total"] == 0  # 2 days late, seen from 3 days ago


def test_overdue_list_is_most_late_first_and_searchable(client, scene, people, laptops, data):
    from tests.test_asset_register import receive_laptops
    from tests.test_receive_serialized import unit

    receive_laptops(client, scene, data, [unit("DL-2001")], reference="INV-2026-0099")  # AST-000003
    created_days_ago("AST-000003", 20)
    assign(client, scene, "AST-000003", people["asha"], assignment_date=days(-12), expected_return_date=days(-6))

    items = client.get(OVERDUE, headers=scene).json()["items"]
    assert [(i["asset"]["asset_code"], i["days_overdue"]) for i in items] == [("AST-000003", 6), ("AST-000001", 2)]

    for term, expected in [("emp-002", ["AST-000001"]), ("asha", ["AST-000003"]), ("dl-2001", ["AST-000003"]), ("zzz", [])]:
        found = client.get(OVERDUE, headers=scene, params={"search": term}).json()["items"]
        assert [i["asset"]["asset_code"] for i in found] == expected
    desc = client.get(OVERDUE, headers=scene, params={"sort": "-expected_return_date"}).json()["items"]
    assert [i["asset"]["asset_code"] for i in desc] == ["AST-000001", "AST-000003"]
    assert error_code(client.get(OVERDUE, headers=scene, params={"sort": "condition_notes"})) == "invalid_sort"


def test_asset_page_flags_an_overdue_holder(client, scene):
    assert client.get(f"{ASSETS}/AST-000001", headers=scene).json()["current_assignment"]["is_overdue"] is True
    assert client.get(f"{ASSETS}/AST-000002", headers=scene).json()["current_assignment"]["is_overdue"] is False


# ---- My Assets (N8, N12, N13) -------------------------------------------------------------------------------------
@pytest.fixture
def asha_login(make_user, login, people):
    user, password = make_user("Employee", employee_id=people["asha"])
    return auth_header(login(user.email, password))


def test_an_employee_sees_only_their_own_assets(client, scene, asha_login):
    response = client.get(MINE, headers=asha_login)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["employee"]["employee_code"] == "EMP-001"
    assert [c["asset"]["asset_code"] for c in body["current"]] == ["AST-000002"]
    assert [p["asset"]["asset_code"] for p in body["past"]] == ["AST-000001"]  # Ravi's current holding not shown
    assert "EMP-002" not in response.text and "Ravi" not in response.text


def test_my_assets_leaves_out_notes_and_staff_emails(client, scene, asha_login):
    """N12: asset, dates, expected return, return date and outcome only."""
    body = client.get(MINE, headers=asha_login).json()
    [past] = body["past"]
    assert past["return_date"] == days(-8) and past["return_outcome"] == "available"
    for hidden in ("condition_notes", "assigned_by", "returned_by", "returned_at", "created_at", "employee"):
        assert hidden not in past
    assert "Minor scratches" not in client.get(MINE, headers=asha_login).text
    assert "@example.com" not in client.get(MINE, headers=asha_login).text


def test_my_assets_shows_my_overdue_item(client, scene, make_user, login, people):
    user, password = make_user("Employee", employee_id=people["ravi"])
    body = client.get(MINE, headers=auth_header(login(user.email, password))).json()
    [current] = body["current"]
    assert (current["asset"]["asset_code"], current["is_overdue"], current["days_overdue"]) == ("AST-000001", True, 2)


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_staff_cannot_open_my_assets(client, staff_headers, scene, role):
    _, headers = staff_headers(role)
    response = client.get(MINE, headers=headers)
    assert response.status_code == 403
    assert error_code(response) == "forbidden"


# ---- Roles and read-only -------------------------------------------------------------------------------------------
def test_employee_role_cannot_see_staff_history_or_overdue(client, scene, asha_login, people):
    for url in (OVERDUE, f"{EMPLOYEES}/{people['asha']}/assignments", f"{EMPLOYEES}/{people['ravi']}/assignments"):
        response = client.get(url, headers=asha_login)
        assert response.status_code == 403, url
        assert error_code(response) == "forbidden"


@pytest.mark.parametrize("role", ["Admin", "IT Manager"])
def test_admin_and_it_manager_can_see_history_and_overdue(client, staff_headers, scene, people, role):
    _, headers = staff_headers(role)
    assert client.get(OVERDUE, headers=headers).status_code == 200
    assert client.get(f"{EMPLOYEES}/{people['asha']}/assignments", headers=headers).status_code == 200


def test_history_endpoints_need_login(client, scene, people):
    for url in (OVERDUE, MINE, f"{EMPLOYEES}/{people['asha']}/assignments"):
        assert client.get(url).status_code == 401, url


def test_reading_history_changes_nothing_and_writes_no_audit_row(client, scene, asha_login, people):
    before = (audit_count(), [(r.id, r.returned_at, r.return_outcome) for r in assignments("AST-000001")])

    client.get(OVERDUE, headers=scene)
    client.get(f"{EMPLOYEES}/{people['asha']}/assignments", headers=scene)
    client.get(MINE, headers=asha_login)

    assert (audit_count(), [(r.id, r.returned_at, r.return_outcome) for r in assignments("AST-000001")]) == before
