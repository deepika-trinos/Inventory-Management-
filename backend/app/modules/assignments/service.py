"""Assignments: giving an Available asset to an active employee (Slice 5.1: ASN-01 to
ASN-04, EMP-05, BR-02, BR-03, BR-05, BR-11; owner's answers N1, N2, N3, N6, N9, A1).

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

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.assets import service as assets_service
from app.modules.assets.models import Asset, AssetStatus
from app.modules.assignments.models import Assignment
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
    }
