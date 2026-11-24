"""Assignments: giving an Available asset to an active employee (Slice 5.1: ASN-01 to
ASN-04, EMP-05, BR-02, BR-03, BR-05, BR-11; owner's answers N1, N2, N3, N6, N9, A1), and
returning it with its inspection (Slice 5.2: ASN-05, ASN-06, BR-04, BR-13; Q5, N4, N5), and
reading the history and overdue returns (Slice 5.3: ASN-07, ASN-08, EMP-04; N7, N8, N10-N13).

RULES
- Only an AVAILABLE asset can be assigned. Assigned, Under Maintenance, Damaged and
  Retired assets are refused, each with its own error code.
- Only an ACTIVE employee can receive an asset (EMP-05, BR-05); a login is not needed (N3).
- Assignment date (N1): today by default (company timezone); earlier allowed; never in
  the future; never before the asset was created (its creation date in the company timezone).
- Expected return date (N2): optional; on or after the assignment date. Not editable later.
- ONE transaction: lock the asset row, check, create the assignment, set the asset to
  Assigned, write audit assignment.created on the asset (so it shows in its history,
  E2). A failure saves nothing.
- Two people assigning the same asset at the same moment: the row lock makes the second
  one wait and then see "already assigned"; the partial unique index
  uq_assignments_open_asset is the final guard.
- An employee who still holds assets cannot be deactivated (N6): see
  open_assignments_for_employee(), used by the employees service.
"""

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.assets import service as assets_service
from app.modules.assets.models import Asset, AssetStatus
from app.modules.assignments.models import CONDITION_NOTES_MAX_LENGTH, Assignment, ReturnOutcome
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.employees.models import Employee
from app.modules.users.models import User

OPEN_ASSET_INDEX = "uq_assignments_open_asset"

# Why each status cannot be assigned (BR-02, BR-03): code and the hint shown to the user.
_NOT_ASSIGNABLE = {
    AssetStatus.ASSIGNED: ("asset_already_assigned", "is already assigned. Return it first."),
    AssetStatus.UNDER_MAINTENANCE: ("asset_under_maintenance", "is Under Maintenance. Finish the repair first."),
    AssetStatus.DAMAGED: ("asset_damaged", "is Damaged. Only Available assets can be assigned."),
    AssetStatus.RETIRED: ("asset_retired", "is retired. A retired asset cannot be assigned."),
}


def _company_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().app_timezone)


def _today() -> date:
    """Today in the company timezone (Q11)."""
    return datetime.now(_company_tz()).date()


def _created_on(asset: Asset) -> date:
    """The day the asset was created, in the company timezone (N1)."""
    return asset.created_at.astimezone(_company_tz()).date()


# ---- Reading ------------------------------------------------------------------------------
def open_assignment(db: Session, asset_id: int) -> Assignment | None:
    """The asset's current (not returned) assignment, if any."""
    return db.scalar(select(Assignment).where(Assignment.asset_id == asset_id, Assignment.returned_at.is_(None)))


def open_assignments_for_assets(db: Session, asset_ids: Iterable[int]) -> dict[int, Assignment]:
    """Current assignments of several assets at once (for the asset register, A1)."""
    ids = list(set(asset_ids))
    if not ids:
        return {}
    rows = db.scalars(select(Assignment).where(Assignment.asset_id.in_(ids), Assignment.returned_at.is_(None)))
    return {row.asset_id: row for row in rows}


def open_assignments_for_employee(db: Session, employee_id: int) -> list[Assignment]:
    """What the employee still holds, by asset ID (N6)."""
    stmt = (
        select(Assignment)
        .join(Asset, Assignment.asset_id == Asset.id)
        .where(Assignment.employee_id == employee_id, Assignment.returned_at.is_(None))
        .order_by(Asset.asset_code)
    )
    return list(db.scalars(stmt).unique())


# ---- Checks -------------------------------------------------------------------------------
def _ensure_assignable(asset: Asset) -> None:
    if asset.status == AssetStatus.AVAILABLE:
        return
    code, hint = _NOT_ASSIGNABLE.get(asset.status, ("asset_not_assignable", "cannot be assigned."))
    raise AppError(409, code, f"{asset.asset_code} {hint}", {"status": asset.status})


def _locked_active_employee(db: Session, employee_id: int) -> Employee:
    """The employee must exist (404) and be active (409, EMP-05, BR-05). Their row is
    share-locked so they cannot be deactivated while this assignment is being saved."""
    employee = db.scalar(
        select(Employee).where(Employee.id == employee_id).with_for_update(read=True, of=Employee)
        .execution_options(populate_existing=True)
    )
    if employee is None:
        raise AppError(404, "employee_not_found", "Employee not found.")
    if not employee.is_active:
        raise AppError(
            409, "employee_inactive",
            f"{employee.full_name} ({employee.employee_code}) is deactivated. Assets cannot be assigned to them.",
        )
    return employee


def _assignment_date(asset: Asset, value: date | None) -> date:
    """N1: today by default; earlier allowed; not in the future; not before the asset was created."""
    today = _today()
    if value is None:
        value = today
    if value > today:
        raise AppError(422, "assignment_date_in_future", "The assignment date cannot be in the future.")
    created_on = _created_on(asset)
    if value < created_on:
        raise AppError(
            422, "assignment_date_before_asset_created",
            f"The assignment date cannot be before {asset.asset_code} was added ({created_on.isoformat()}).",
            {"asset_created_on": created_on.isoformat()},
        )
    return value


def _expected_return_date(value: date | None, assignment_date: date) -> date | None:
    """N2: optional; on or after the assignment date."""
    if value is not None and value < assignment_date:
        raise AppError(
            422, "invalid_expected_return_date",
            f"The expected return date cannot be before the assignment date ({assignment_date.isoformat()}).",
        )
    return value


def _audit_after(assignment: Assignment, employee: Employee) -> dict[str, Any]:
    return {
        "status": AssetStatus.ASSIGNED,
        "assignment_id": assignment.id,
        "employee_id": employee.id,
        "employee_code": employee.employee_code,
        "employee_name": employee.full_name,
        "assignment_date": assignment.assignment_date,
        "expected_return_date": assignment.expected_return_date,
    }


# ---- Assigning ----------------------------------------------------------------------------
def assign_asset(
    db: Session,
    *,
    actor: User,
    asset: Asset,
    employee_id: int,
    assignment_date: date | None = None,
    expected_return_date: date | None = None,
    context: AuditContext | None = None,
) -> Assignment:
    """Give the asset to the employee (ASN-01 to ASN-04). One transaction with the
    audit row; a failure saves nothing.

    Errors: 409 `asset_already_assigned` / `asset_under_maintenance` / `asset_damaged` /
    `asset_retired`; 404 `employee_not_found`; 409 `employee_inactive`; 422
    `assignment_date_in_future`, `assignment_date_before_asset_created`,
    `invalid_expected_return_date`."""
    try:
        asset = assets_service._lock(db, asset)  # the second of two simultaneous assigns waits here
        _ensure_assignable(asset)
        employee = _locked_active_employee(db, employee_id)
        on = _assignment_date(asset, assignment_date)
        expected = _expected_return_date(expected_return_date, on)

        assignment = Assignment(
            asset_id=asset.id,
            employee_id=employee.id,
            assignment_date=on,
            expected_return_date=expected,
            assigned_by_user_id=actor.id,
        )
        db.add(assignment)
        asset.status = AssetStatus.ASSIGNED
        db.flush()
        audit.record(
            db, actor=actor, action=AuditAction.ASSIGNMENT_CREATED, entity=asset,
            before={"status": AssetStatus.AVAILABLE}, after=_audit_after(assignment, employee), context=context,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if OPEN_ASSET_INDEX in str(exc.orig):
            raise AppError(
                409, "asset_already_assigned", f"{asset.asset_code} is already assigned. Return it first.",
                {"status": AssetStatus.ASSIGNED},
            ) from None
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(assignment)
    return assignment


# ---- Returning (Slice 5.2: ASN-05, ASN-06, BR-04, BR-13; owner's answers Q5, N4, N5, N9) ----------
_OUTCOME_LABELS = {
    ReturnOutcome.AVAILABLE: "Available",
    ReturnOutcome.UNDER_MAINTENANCE: "Under Maintenance",
    ReturnOutcome.DAMAGED: "Damaged",
}


def _lock_open_assignment(db: Session, asset: Asset) -> Assignment:
    """The asset's open assignment, row-locked. The asset row is already locked, so a
    second return at the same moment waits and then finds the asset no longer Assigned."""
    assignment = db.scalar(
        select(Assignment)
        .where(Assignment.asset_id == asset.id, Assignment.returned_at.is_(None))
        .with_for_update(of=Assignment)
        .execution_options(populate_existing=True)
    )
    if asset.status != AssetStatus.ASSIGNED or assignment is None:
        raise AppError(
            409, "asset_not_assigned",
            f"{asset.asset_code} is not assigned to anyone, so it cannot be returned.",
            {"status": asset.status},
        )
    return assignment


def _return_date(value: date | None, assignment: Assignment) -> date:
    """N4: today by default; earlier allowed; never in the future; not before the assignment date."""
    today = _today()
    if value is None:
        value = today
    if value > today:
        raise AppError(422, "return_date_in_future", "The return date cannot be in the future.")
    if value < assignment.assignment_date:
        raise AppError(
            422, "return_date_before_assignment",
            f"The return date cannot be before the assignment date ({assignment.assignment_date.isoformat()}).",
            {"assignment_date": assignment.assignment_date.isoformat()},
        )
    return value


def _outcome(value: str | None) -> str:
    """N4: required; Available, Under Maintenance or Damaged."""
    if value not in ReturnOutcome.ALL:
        raise AppError(
            422, "invalid_inspection_outcome",
            "Please choose the inspection outcome: Available, Under Maintenance or Damaged.",
        )
    return value


def _condition_notes(value: str | None, outcome: str) -> str | None:
    """N4: up to 1,000 characters; optional for Available, required for Damaged or Under Maintenance."""
    notes = (value or "").strip() or None
    if notes is None and outcome != ReturnOutcome.AVAILABLE:
        raise AppError(
            422, "condition_notes_required",
            f"Please describe the condition: notes are required when the outcome is {_OUTCOME_LABELS[outcome]}.",
        )
    if notes is not None and len(notes) > CONDITION_NOTES_MAX_LENGTH:
        raise AppError(
            422, "invalid_condition_notes",
            f"The condition notes can be at most {CONDITION_NOTES_MAX_LENGTH:,} characters.",
        )
    return notes


def return_asset(
    db: Session,
    *,
    actor: User,
    asset: Asset,
    inspection_outcome: str | None,
    return_date: date | None = None,
    condition_notes: str | None = None,
    context: AuditContext | None = None,
) -> Assignment:
    """Record the return and the inspection on the same form (ASN-05, ASN-06, BR-04, Q5).
    Closes the open assignment (kept, never overwritten, ASN-07) and sets the asset's status
    from the outcome. Under Maintenance sets the status only; no maintenance request (N5).
    One transaction with audit assignment.returned; a failure saves nothing.

    Errors: 409 `asset_not_assigned`; 422 `invalid_inspection_outcome`,
    `condition_notes_required`, `invalid_condition_notes`, `return_date_in_future`,
    `return_date_before_assignment`."""
    try:
        asset = assets_service._lock(db, asset)  # the second of two simultaneous returns waits here
        assignment = _lock_open_assignment(db, asset)
        outcome = _outcome(inspection_outcome)
        notes = _condition_notes(condition_notes, outcome)
        on = _return_date(return_date, assignment)

        assignment.return_date = on
        assignment.return_outcome = outcome
        assignment.condition_notes = notes
        assignment.returned_at = func.now()  # database time, like the audit row
        assignment.returned_by_user_id = actor.id
        asset.status = outcome
        employee = assignment.employee
        audit.record(
            db, actor=actor, action=AuditAction.ASSIGNMENT_RETURNED, entity=asset,
            before={"status": AssetStatus.ASSIGNED},
            after={
                "status": outcome,
                "assignment_id": assignment.id,
                "employee_id": employee.id,
                "employee_code": employee.employee_code,
                "employee_name": employee.full_name,
                "assignment_date": assignment.assignment_date,
                "return_date": on,
                "inspection_outcome": outcome,
                "condition_notes": notes,
            },
            context=context,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(assignment)
    return assignment


# ---- History and overdue (Slice 5.3: ASN-07, ASN-08, EMP-04; owner's answers N7, N8, N10-N13) ----
def days_overdue(assignment: Assignment, today: date | None = None) -> int:
    """N7: how many days past the expected return date an OPEN assignment is (0 = not overdue).
    Overdue = expected return date before today (company timezone) and not returned. Due today
    is not overdue yet; no expected return date is never overdue; a returned one is never overdue."""
    if assignment.returned_at is not None or assignment.expected_return_date is None:
        return 0
    today = today or _today()
    return max((today - assignment.expected_return_date).days, 0)


def employee_assignments(db: Session, employee_id: int) -> dict[str, list[Assignment]]:
    """EMP-04: what the employee holds now and what they held before (ASN-07). Current: by
    assignment date, oldest first. Past: newest return first. Works for inactive employees."""
    rows = list(
        db.scalars(
            select(Assignment)
            .where(Assignment.employee_id == employee_id)
            .order_by(Assignment.assignment_date, Assignment.id)
        ).unique()
    )
    current = [a for a in rows if a.returned_at is None]
    past = sorted(
        (a for a in rows if a.returned_at is not None),
        key=lambda a: (a.return_date, a.returned_at, a.id),
        reverse=True,
    )
    return {"current": current, "past": past}


_OVERDUE_SORTABLE = {
    "expected_return_date": Assignment.expected_return_date,
    "assignment_date": Assignment.assignment_date,
    "asset_code": Asset.asset_code,
    "employee": func.lower(Employee.full_name),
}


def list_overdue(db: Session, params, *, search: str | None = None) -> dict[str, Any]:
    """ASN-08, N7, N10: every overdue assignment, most late first (oldest expected return date),
    paged. `search` matches part of the asset ID, asset name, serial number, employee ID or
    employee name, ignoring case."""
    from app.core.pagination import paginate

    stmt = (
        select(Assignment)
        .join(Asset, Assignment.asset_id == Asset.id)
        .join(Employee, Assignment.employee_id == Employee.id)
        .where(
            Assignment.returned_at.is_(None),
            Assignment.expected_return_date.is_not(None),
            Assignment.expected_return_date < _today(),
        )
    )
    if search and search.strip():
        term = search.strip().lower()
        stmt = stmt.where(
            func.lower(Asset.asset_code).contains(term, autoescape=True)
            | func.lower(Asset.name).contains(term, autoescape=True)
            | func.lower(Asset.serial_number).contains(term, autoescape=True)
            | func.lower(Employee.employee_code).contains(term, autoescape=True)
            | func.lower(Employee.full_name).contains(term, autoescape=True)
        )
    return paginate(
        db, stmt, params, sortable=_OVERDUE_SORTABLE, default_sort="expected_return_date", tiebreaker=Assignment.id
    )


def employee_of_login(db: Session, user: User) -> Employee:
    """N8: the employee record linked to this login (every Employee-role login has one, order fix b)."""
    employee = db.get(Employee, user.employee_id) if user.employee_id is not None else None
    if employee is None:
        raise AppError(404, "employee_not_linked", "Your login is not linked to an employee record. Ask an Admin.")
    return employee


def read(assignment: Assignment, *, for_employee: bool = False, today: date | None = None) -> dict[str, Any]:
    """One assignment as the history and overdue responses show it. `for_employee` leaves out the
    condition notes and the staff who assigned or returned it (N12)."""
    asset = assignment.asset
    employee = assignment.employee
    late = days_overdue(assignment, today)
    data: dict[str, Any] = {
        "id": assignment.id,
        "asset": {
            "id": asset.id, "asset_code": asset.asset_code, "name": asset.name,
            "serial_number": asset.serial_number, "status": asset.status,
        },
        "employee": {
            "id": employee.id, "employee_code": employee.employee_code,
            "full_name": employee.full_name, "status": employee.status,
        },
        "assignment_date": assignment.assignment_date,
        "expected_return_date": assignment.expected_return_date,
        "return_date": assignment.return_date,
        "return_outcome": assignment.return_outcome,
        "is_open": assignment.returned_at is None,
        "is_overdue": late > 0,
        "days_overdue": late,
    }
    if not for_employee:
        data.update(
            assigned_by=assignment.assigned_by,
            created_at=assignment.created_at,
            condition_notes=assignment.condition_notes,
            returned_by=assignment.returned_by,
            returned_at=assignment.returned_at,
        )
    return data


# ---- Response helpers -----------------------------------------------------------------------
def summary(assignment: Assignment | None) -> dict[str, Any] | None:
    """The current assignment as the asset responses show it."""
    if assignment is None:
        return None
    employee = assignment.employee
    return {
        "id": assignment.id,
        "employee": {
            "id": employee.id,
            "employee_code": employee.employee_code,
            "full_name": employee.full_name,
            "status": employee.status,
        },
        "assignment_date": assignment.assignment_date,
        "expected_return_date": assignment.expected_return_date,
        "assigned_by": assignment.assigned_by,
        "created_at": assignment.created_at,
        "is_overdue": days_overdue(assignment) > 0,  # Slice 5.3, N7
    }
