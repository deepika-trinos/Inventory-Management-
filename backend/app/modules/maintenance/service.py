"""Maintenance requests: reporting a problem with an asset (Slice 6.1: MNT-01 to MNT-03; owner's
answers Q9, Q10, Q13, N5, O1-O14; decisions M1-M8 in decisions.md section 32).

RULES
- Staff (Admin, IT Manager) can report on ANY asset except a Retired one (MNT-02, O1); they may
  set a priority (Q10) and a reported date (O5: today by default, earlier allowed, never in the
  future, never before the asset was created).
- An Employee can report only on an asset they HOLD NOW (MNT-01, O3, O6). Anything else - a
  missing asset, someone else's asset, one they returned - is "asset not found" (O7), so other
  people's assets cannot be discovered (PRD 4.1). No priority (Q10, O8); the date is today (O5).
- Issue: required, trimmed, up to 1,000 characters (O4).
- ONE open request (Reported or In Progress) per asset (O2): checked after locking the asset row;
  the partial unique index uq_maintenance_requests_open_asset is the final guard.
- Reporting NEVER changes the asset's status (Q9).
- ONE transaction: the request and audit maintenance.reported (on the asset, so it shows in its
  history, E2 / O14). A failure saves nothing.
"""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.modules.assets import service as assets_service
from app.modules.assets.models import Asset, AssetStatus
from app.modules.assignments.models import Assignment
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.employees.models import Employee
from app.modules.maintenance.models import ISSUE_MAX_LENGTH, MaintenanceRequest, MaintenanceStatus
from app.modules.users.models import User

OPEN_ASSET_INDEX = "uq_maintenance_requests_open_asset"


def _company_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().app_timezone)


def _today() -> date:
    """Today in the company timezone (Q11)."""
    return datetime.now(_company_tz()).date()


# ---- Reading ------------------------------------------------------------------------------------
def open_request(db: Session, asset_id: int) -> MaintenanceRequest | None:
    """The asset's open (Reported or In Progress) request, if any (O2)."""
    return db.scalar(
        select(MaintenanceRequest).where(
            MaintenanceRequest.asset_id == asset_id, MaintenanceRequest.status.in_(MaintenanceStatus.OPEN)
        )
    )


def open_requests_for_assets(db: Session, asset_ids: list[int]) -> dict[int, MaintenanceRequest]:
    """Open requests of several assets at once (the My Assets note, M7)."""
    ids = list(set(asset_ids))
    if not ids:
        return {}
    rows = db.scalars(
        select(MaintenanceRequest).where(
            MaintenanceRequest.asset_id.in_(ids), MaintenanceRequest.status.in_(MaintenanceStatus.OPEN)
        )
    )
    return {row.asset_id: row for row in rows}


def requests_for_asset(db: Session, asset: Asset) -> list[MaintenanceRequest]:
    """Every request of the asset, newest first (M7). Not paged: one asset's requests stay few."""
    stmt = (
        select(MaintenanceRequest)
        .where(MaintenanceRequest.asset_id == asset.id)
        .order_by(MaintenanceRequest.id.desc())
    )
    return list(db.scalars(stmt).unique())


_PRIORITY_ORDER = case({"low": 1, "medium": 2, "high": 3}, value=MaintenanceRequest.priority, else_=0)

_SORTABLE = {
    "request_number": MaintenanceRequest.request_number,
    "reported_date": MaintenanceRequest.reported_date,
    "priority": _PRIORITY_ORDER,
    "status": MaintenanceRequest.status,
    "asset_code": Asset.asset_code,
}


def list_requests(
    db: Session, params: PageParams, *, search: str | None = None, status: str | None = None
) -> dict[str, Any]:
    """Every request, newest first, paged (M7, O12). `search` matches part of the request number,
    asset ID, asset name or serial number, ignoring case; `status` filters."""
    stmt = select(MaintenanceRequest).join(Asset, MaintenanceRequest.asset_id == Asset.id)
    if status:
        stmt = stmt.where(MaintenanceRequest.status == status)
    if search and search.strip():
        term = search.strip().lower()
        stmt = stmt.where(
            func.lower(MaintenanceRequest.request_number).contains(term, autoescape=True)
            | func.lower(Asset.asset_code).contains(term, autoescape=True)
            | func.lower(Asset.name).contains(term, autoescape=True)
            | func.lower(Asset.serial_number).contains(term, autoescape=True)
        )
    return paginate(
        db, stmt, params, sortable=_SORTABLE, default_sort="-request_number", tiebreaker=MaintenanceRequest.id
    )


# ---- Checks -------------------------------------------------------------------------------------
def _issue(value: str | None) -> str:
    """O4: required, trimmed, up to 1,000 characters."""
    issue = (value or "").strip()
    if not issue:
        raise AppError(422, "invalid_issue_description", "Please describe the problem.")
    if len(issue) > ISSUE_MAX_LENGTH:
        raise AppError(
            422, "invalid_issue_description",
            f"The problem description can be at most {ISSUE_MAX_LENGTH:,} characters.",
        )
    return issue


def _reported_date(asset: Asset, value: date | None) -> date:
    """O5 (staff): today by default; earlier allowed; never in the future; not before the asset was created."""
    today = _today()
    if value is None:
        return today
    if value > today:
        raise AppError(422, "reported_date_in_future", "The reported date cannot be in the future.")
    created_on = asset.created_at.astimezone(_company_tz()).date()
    if value < created_on:
        raise AppError(
            422, "reported_date_before_asset_created",
            f"The reported date cannot be before {asset.asset_code} was added ({created_on.isoformat()}).",
            {"asset_created_on": created_on.isoformat()},
        )
    return value


def _open_request_error(asset: Asset, request_number: str | None) -> AppError:
    number = request_number or "A request"
    return AppError(
        409, "maintenance_request_open",
        f"{number} is already open for {asset.asset_code}. Only one open request per asset is allowed.",
        {"request_number": request_number},
    )


def _ensure_no_open_request(db: Session, asset: Asset) -> None:
    """O2: one open (Reported or In Progress) request per asset."""
    existing = open_request(db, asset.id)
    if existing is not None:
        raise _open_request_error(asset, existing.request_number)


def _not_found() -> AppError:
    return AppError(404, "asset_not_found", "Asset not found.")


def held_asset(db: Session, employee: Employee, asset_id: int) -> Asset:
    """O3, O6, O7: the asset, only if this employee holds it NOW; otherwise 'not found'."""
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise _not_found()
    held = db.scalar(
        select(Assignment.id).where(
            Assignment.asset_id == asset.id,
            Assignment.employee_id == employee.id,
            Assignment.returned_at.is_(None),
        )
    )
    if held is None:
        raise _not_found()
    return asset


# ---- Reporting ----------------------------------------------------------------------------------
def report_problem(
    db: Session,
    *,
    actor: User,
    asset: Asset,
    issue_description: str | None,
    priority: str | None = None,
    reported_date: date | None = None,
    holder: Employee | None = None,
    context: AuditContext | None = None,
) -> MaintenanceRequest:
    """Open a maintenance request with status Reported (MNT-01 to MNT-03). The asset's status is
    not changed (Q9). One transaction with audit maintenance.reported; a failure saves nothing.

    `holder` is given for an Employee's report (MNT-01): after the asset row is locked, the
    asset must still be held by that employee (O3, O6), otherwise 404 `asset_not_found` (O7).
    Employees never pass a priority or a date (Q10, O5); the route makes sure of that.

    Errors: 404 `asset_not_found`; 409 `asset_retired`, `maintenance_request_open`; 422
    `invalid_issue_description`, `reported_date_in_future`, `reported_date_before_asset_created`."""
    try:
        asset = assets_service._lock(db, asset)  # the second of two simultaneous reports waits here
        if holder is not None:
            held_asset(db, holder, asset.id)  # re-checked under the lock: returned meanwhile -> 404
        if asset.status == AssetStatus.RETIRED:
            raise AppError(
                409, "asset_retired", f"{asset.asset_code} is retired. A problem cannot be reported for it.",
                {"status": asset.status},
            )
        issue = _issue(issue_description)
        on = _today() if holder is not None else _reported_date(asset, reported_date)
        _ensure_no_open_request(db, asset)

        request = MaintenanceRequest(
            asset_id=asset.id,
            issue_description=issue,
            priority=priority,
            status=MaintenanceStatus.REPORTED,
            reported_date=on,
            reported_by_user_id=actor.id,
        )
        db.add(request)
        db.flush()
        audit.record(
            db, actor=actor, action=AuditAction.MAINTENANCE_REPORTED, entity=asset,
            after={
                "request_id": request.id,
                "request_number": request.request_number,
                "issue_description": issue,
                "priority": priority,
                "reported_date": on,
                "status": MaintenanceStatus.REPORTED,
                "reported_by_role": actor.role.name,
            },
            context=context,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if OPEN_ASSET_INDEX in str(exc.orig):
            existing = open_request(db, asset.id)
            raise _open_request_error(asset, existing.request_number if existing else None) from None
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(request)
    return request


# ---- Response helpers ---------------------------------------------------------------------------
def read(request: MaintenanceRequest) -> dict[str, Any]:
    """One request as the staff responses show it (M7)."""
    asset = request.asset
    reporter = request.reported_by
    return {
        "id": request.id,
        "request_number": request.request_number,
        "asset": {
            "id": asset.id, "asset_code": asset.asset_code, "name": asset.name,
            "serial_number": asset.serial_number, "status": asset.status,
        },
        "issue_description": request.issue_description,
        "priority": request.priority,
        "status": request.status,
        "reported_date": request.reported_date,
        "reported_by": {"id": reporter.id, "email": reporter.email, "role": reporter.role.name},
        "created_at": request.created_at,
    }


def summary(request: MaintenanceRequest | None) -> dict[str, Any] | None:
    """The short form shown to an Employee: number, status and date only (M7)."""
    if request is None:
        return None
    return {
        "request_number": request.request_number,
        "status": request.status,
        "reported_date": request.reported_date,
    }
