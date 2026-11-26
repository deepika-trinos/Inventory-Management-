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

REPAIR PROGRESS (Slice 6.2: MNT-04 to MNT-07, BR-05; owner's answers S1-S14; decisions U1-U9)
- Reported -> In Progress (start work): the asset becomes Under Maintenance (Q9). Refused while the
  asset is Assigned ("Return it first.", S1) or Retired.
- In Progress -> Completed: completion date and repair notes required (S5); the asset STAYS Under
  Maintenance until the Slice 6.3 inspection (MNT-07).
- Reported or In Progress -> Cancelled: required reason (S11). From Reported the asset is unchanged;
  from In Progress it stays Under Maintenance (S2).
- Everything else is refused (S3, S4: Completed and Cancelled are final).
- Priority and details (provider, notes, cost) can be edited while the request is open (S6, S9, S10, S12).
- Every change: lock the asset row, then the request row; save the change, the asset's status and the
  audit row (maintenance.status_changed / maintenance.updated, on the asset, U6) together.

COMPLETION INSPECTION (Slice 6.3: MNT-07, workflow 7.4; owner's answers in decisions.md section 35)
- A request that is Completed, or Cancelled after work started, is AWAITING INSPECTION; the asset is
  still Under Maintenance. A request cancelled before work started never changed the asset: no inspection.
- Inspect (Admin, IT Manager): outcome Available, Damaged or Retired becomes the asset's status.
  Inspection date today by default, earlier allowed, not before the completion date (or the day it was
  cancelled), never in the future. Condition notes up to 1,000: optional for Available, required for
  Damaged and Retired; for Retired they are the retirement reason, so at most 500 (A3).
- Retired through inspection: the one way to retire an asset that is Under Maintenance (revises A3).
  The asset gets the same retirement record (F2) and the same asset.retired audit row as Retire...
- Once, and final. One transaction: the request, the asset, maintenance.inspected (and asset.retired).
- While a request awaits inspection, no new request can be reported for the asset (revises O2).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.pagination import PageParams, paginate
from app.modules.assets import service as assets_service
from app.modules.assets.models import RETIRE_REASON_MAX_LENGTH, Asset, AssetStatus
from app.modules.assignments.models import Assignment
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction
from app.modules.audit.service import AuditContext
from app.modules.employees.models import Employee
from app.modules.audit.models import AuditLog
from app.modules.maintenance.models import (
    CANCEL_REASON_MAX_LENGTH,
    INSPECTION_NOTES_MAX_LENGTH,
    ISSUE_MAX_LENGTH,
    REPAIR_NOTES_MAX_LENGTH,
    REQUEST_NUMBER_PREFIX,
    SERVICE_PROVIDER_MAX_LENGTH,
    InspectionOutcome,
    MaintenanceRequest,
    MaintenanceStatus,
)
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


def _awaiting_inspection_clause():
    """Slice 6.3: work started, Completed or Cancelled, not yet inspected."""
    return (
        MaintenanceRequest.status.in_((MaintenanceStatus.COMPLETED, MaintenanceStatus.CANCELLED))
        & MaintenanceRequest.started_at.is_not(None)
        & MaintenanceRequest.inspected_at.is_(None)
    )


def awaiting_inspection_request(db: Session, asset_id: int) -> MaintenanceRequest | None:
    """The asset's request awaiting inspection, if any (Slice 6.3)."""
    return db.scalar(
        select(MaintenanceRequest).where(MaintenanceRequest.asset_id == asset_id, _awaiting_inspection_clause())
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


AWAITING_INSPECTION_FILTER = "awaiting_inspection"  # Slice 6.3: a list filter, not a stored status


def list_requests(
    db: Session, params: PageParams, *, search: str | None = None, status: str | None = None
) -> dict[str, Any]:
    """Every request, newest first, paged (M7, O12). `search` matches part of the request number,
    asset ID, asset name or serial number, ignoring case; `status` filters."""
    stmt = select(MaintenanceRequest).join(Asset, MaintenanceRequest.asset_id == Asset.id)
    if status == AWAITING_INSPECTION_FILTER:
        stmt = stmt.where(_awaiting_inspection_clause())
    elif status:
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


def _awaiting_inspection_error(asset: Asset, request_number: str) -> AppError:
    return AppError(
        409, "maintenance_request_awaiting_inspection",
        f"{request_number} is awaiting inspection for {asset.asset_code}. Inspect the asset first.",
        {"request_number": request_number},
    )


def _ensure_no_open_request(db: Session, asset: Asset) -> None:
    """O2: one open (Reported or In Progress) request per asset; Slice 6.3: and none while a request
    awaits inspection."""
    existing = open_request(db, asset.id)
    if existing is not None:
        raise _open_request_error(asset, existing.request_number)
    waiting = awaiting_inspection_request(db, asset.id)
    if waiting is not None:
        raise _awaiting_inspection_error(asset, waiting.request_number)


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
            waiting = awaiting_inspection_request(db, asset.id)
            if waiting is not None:
                raise _awaiting_inspection_error(asset, waiting.request_number) from None
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
        # Slice 6.2 (U1)
        "started_date": request.started_date,
        "started_at": request.started_at,
        "started_by": _user(request.started_by),
        "service_provider": request.service_provider,
        "repair_notes": request.repair_notes,
        "cost": request.cost,
        "completion_date": request.completion_date,
        "completed_at": request.completed_at,
        "completed_by": _user(request.completed_by),
        "cancelled_at": request.cancelled_at,
        "cancelled_by": _user(request.cancelled_by),
        "cancel_reason": request.cancel_reason,
        # Slice 6.3
        "awaiting_inspection": request.awaiting_inspection,
        "inspection_outcome": request.inspection_outcome,
        "inspection_date": request.inspection_date,
        "inspection_notes": request.inspection_notes,
        "inspected_at": request.inspected_at,
        "inspected_by": _user(request.inspected_by),
    }


def _user(user: User | None) -> dict[str, Any] | None:
    return {"id": user.id, "email": user.email, "role": user.role.name} if user is not None else None


def summary(request: MaintenanceRequest | None) -> dict[str, Any] | None:
    """The short form shown to an Employee: number, status and date only (M7)."""
    if request is None:
        return None
    return {
        "request_number": request.request_number,
        "status": request.status,
        "reported_date": request.reported_date,
    }


# ---- Repair progress (Slice 6.2) ------------------------------------------------------------------
_STATUS_LABELS = {
    MaintenanceStatus.REPORTED: "Reported",
    MaintenanceStatus.IN_PROGRESS: "In Progress",
    MaintenanceStatus.COMPLETED: "Completed",
    MaintenanceStatus.CANCELLED: "Cancelled",
}

# Which moves are allowed (U3, S3, S4): target status -> statuses it can come from.
_ALLOWED_MOVES = {
    MaintenanceStatus.IN_PROGRESS: {MaintenanceStatus.REPORTED},
    MaintenanceStatus.COMPLETED: {MaintenanceStatus.IN_PROGRESS},
    MaintenanceStatus.CANCELLED: {MaintenanceStatus.REPORTED, MaintenanceStatus.IN_PROGRESS},
}

PROVIDER_LABEL = "service provider or responsible person"


def get_request(db: Session, ref: str | int) -> MaintenanceRequest:
    """One request by its id (e.g. 5) or its number (e.g. "MNT-000005", any case)."""
    text_ref = str(ref).strip()
    request: MaintenanceRequest | None = None
    if text_ref.isdigit():
        request = db.get(MaintenanceRequest, int(text_ref))
    elif text_ref.upper().startswith(REQUEST_NUMBER_PREFIX):
        request = db.scalar(select(MaintenanceRequest).where(MaintenanceRequest.request_number == text_ref.upper()))
    if request is None:
        raise AppError(404, "maintenance_request_not_found", "Maintenance request not found.")
    return request


def request_history(db: Session, request: MaintenanceRequest) -> list[dict[str, Any]]:
    """The request's history (S13, U6): the asset's audit rows that belong to this request, newest first."""
    rows = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.entity_type == Asset.__tablename__,
            AuditLog.entity_id == str(request.asset_id),
            AuditLog.action.like("maintenance.%"),
            AuditLog.after_data["request_id"].astext == str(request.id),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    ).all()
    actor_ids = {r.actor_user_id for r in rows if r.actor_user_id is not None}
    actors = {u.id: u for u in db.scalars(select(User).where(User.id.in_(actor_ids)))} if actor_ids else {}
    return [
        {
            "id": r.id, "action": r.action, "created_at": r.created_at, "actor": actors.get(r.actor_user_id),
            "before": r.before_data, "after": r.after_data,
        }
        for r in rows
    ]


def _lock_both(db: Session, request: MaintenanceRequest) -> tuple[Asset, MaintenanceRequest]:
    """Lock the asset row first, then the request row (always in this order, U5), and re-read both."""
    asset = assets_service._lock(db, request.asset)
    locked = db.scalars(
        select(MaintenanceRequest)
        .where(MaintenanceRequest.id == request.id)
        .with_for_update(of=MaintenanceRequest)
        .execution_options(populate_existing=True)
    ).unique().one()
    return asset, locked


def _ensure_move(request: MaintenanceRequest, to: str) -> None:
    if request.status in _ALLOWED_MOVES[to]:
        return
    frm, dest = _STATUS_LABELS[request.status], _STATUS_LABELS[to]
    if request.status in (MaintenanceStatus.COMPLETED, MaintenanceStatus.CANCELLED):
        hint = f"{request.request_number} is {frm} and cannot be changed any more."
    else:
        hint = f"{request.request_number} cannot go from {frm} to {dest}."
        if to == MaintenanceStatus.COMPLETED:
            hint += " Start work first."
    raise AppError(409, "invalid_status_change", hint, {"from": request.status, "to": to})


def _clean(value: str | None, *, max_length: int, code: str, label: str, required: bool = False) -> str | None:
    text_value = (value or "").strip() or None
    if text_value is None and required:
        raise AppError(422, code, f"Please enter the {label}.")
    if text_value is not None and len(text_value) > max_length:
        raise AppError(422, code, f"The {label} can be at most {max_length:,} characters.")
    return text_value


def _provider(value: str | None) -> str | None:
    return _clean(value, max_length=SERVICE_PROVIDER_MAX_LENGTH, code="invalid_service_provider", label=PROVIDER_LABEL)


def _started_date(request: MaintenanceRequest, value: date | None) -> date:
    """S8: today by default; earlier allowed; never in the future; not before the reported date."""
    today = _today()
    on = value or today
    if on > today:
        raise AppError(422, "started_date_in_future", "The work started date cannot be in the future.")
    if on < request.reported_date:
        raise AppError(
            422, "started_date_before_reported",
            f"Work cannot start before the problem was reported ({request.reported_date.isoformat()}).",
            {"reported_date": request.reported_date.isoformat()},
        )
    return on


def _completion_date(request: MaintenanceRequest, value: date | None) -> date:
    """S7: today by default; earlier allowed; never in the future; not before the start date."""
    today = _today()
    on = value or today
    if on > today:
        raise AppError(422, "completion_date_in_future", "The completion date cannot be in the future.")
    if request.started_date is not None and on < request.started_date:
        raise AppError(
            422, "completion_date_before_start",
            f"The completion date cannot be before work started ({request.started_date.isoformat()}).",
            {"started_date": request.started_date.isoformat()},
        )
    return on


def _money(value: Decimal | None) -> Decimal | None:
    """S6: always 2 decimals, so the request and its audit row show the same amount (300 -> 300.00)."""
    return value.quantize(Decimal("0.01")) if value is not None else None


def _ids(request: MaintenanceRequest) -> dict[str, Any]:
    return {"request_id": request.id, "request_number": request.request_number}


def _audit_and_commit(db: Session, *, actor: User, asset: Asset, action: str, before: dict, after: dict, context) -> None:
    audit.record(db, actor=actor, action=action, entity=asset, before=before, after=after, context=context)
    db.commit()


def start_work(
    db: Session, *, actor: User, request: MaintenanceRequest, started_date: date | None = None,
    service_provider: str | None = None, context: AuditContext | None = None,
) -> MaintenanceRequest:
    """Reported -> In Progress (MNT-04). The asset becomes Under Maintenance (Q9) and cannot be
    assigned (BR-05). Refused while the asset is Assigned (S1) or Retired.

    Errors: 409 `invalid_status_change`, `asset_assigned`, `asset_retired`; 422
    `started_date_in_future`, `started_date_before_reported`, `invalid_service_provider`."""
    try:
        asset, request = _lock_both(db, request)
        _ensure_move(request, MaintenanceStatus.IN_PROGRESS)
        if asset.status == AssetStatus.ASSIGNED:
            raise AppError(
                409, "asset_assigned",
                f"{asset.asset_code} is assigned to an employee. Return it first, then start work.",
                {"status": asset.status},
            )
        if asset.status == AssetStatus.RETIRED:
            raise AppError(409, "asset_retired", f"{asset.asset_code} is retired.", {"status": asset.status})
        on = _started_date(request, started_date)
        provider = _provider(service_provider)

        before = {**_ids(request), "status": request.status, "asset_status": asset.status}
        request.status = MaintenanceStatus.IN_PROGRESS
        request.started_date = on
        request.started_at = func.now()  # database time, like the audit row
        request.started_by_user_id = actor.id
        if provider is not None:
            request.service_provider = provider
        asset.status = AssetStatus.UNDER_MAINTENANCE
        after = {
            **_ids(request), "status": MaintenanceStatus.IN_PROGRESS, "asset_status": asset.status,
            "started_date": on, "service_provider": request.service_provider,
        }
        _audit_and_commit(
            db, actor=actor, asset=asset, action=AuditAction.MAINTENANCE_STATUS_CHANGED,
            before=before, after=after, context=context,
        )
    except Exception:
        db.rollback()
        raise
    db.refresh(request)
    return request


def complete_work(
    db: Session, *, actor: User, request: MaintenanceRequest, repair_notes: str | None,
    completion_date: date | None = None, service_provider: str | None = None, cost: Decimal | None = None,
    context: AuditContext | None = None,
) -> MaintenanceRequest:
    """In Progress -> Completed (MNT-04, MNT-05). Completion date and repair notes required (S5); the
    asset stays Under Maintenance until the Slice 6.3 inspection (MNT-07).

    Errors: 409 `invalid_status_change`; 422 `invalid_repair_notes`, `completion_date_in_future`,
    `completion_date_before_start`, `invalid_service_provider`."""
    try:
        asset, request = _lock_both(db, request)
        _ensure_move(request, MaintenanceStatus.COMPLETED)
        notes = _clean(
            repair_notes, max_length=REPAIR_NOTES_MAX_LENGTH, code="invalid_repair_notes",
            label="repair notes (what was done)", required=True,
        )
        on = _completion_date(request, completion_date)
        provider = _provider(service_provider)

        before = {**_ids(request), "status": request.status}
        request.status = MaintenanceStatus.COMPLETED
        request.repair_notes = notes
        request.completion_date = on
        request.completed_at = func.now()
        request.completed_by_user_id = actor.id
        if provider is not None:
            request.service_provider = provider
        if cost is not None:
            request.cost = _money(cost)
        after = {
            **_ids(request), "status": MaintenanceStatus.COMPLETED, "asset_status": asset.status,
            "completion_date": on, "repair_notes": notes, "service_provider": request.service_provider,
            "cost": request.cost,
        }
        _audit_and_commit(
            db, actor=actor, asset=asset, action=AuditAction.MAINTENANCE_STATUS_CHANGED,
            before=before, after=after, context=context,
        )
    except Exception:
        db.rollback()
        raise
    db.refresh(request)
    return request


def cancel_request(
    db: Session, *, actor: User, request: MaintenanceRequest, reason: str | None,
    context: AuditContext | None = None,
) -> MaintenanceRequest:
    """Reported or In Progress -> Cancelled (MNT-04, S11). From Reported the asset is unchanged; from
    In Progress it stays Under Maintenance until the Slice 6.3 inspection (S2). Final (S4).

    Errors: 409 `invalid_status_change`; 422 `invalid_cancel_reason`."""
    try:
        asset, request = _lock_both(db, request)
        _ensure_move(request, MaintenanceStatus.CANCELLED)
        clean_reason = _clean(
            reason, max_length=CANCEL_REASON_MAX_LENGTH, code="invalid_cancel_reason",
            label="reason for cancelling", required=True,
        )
        before = {**_ids(request), "status": request.status}
        request.status = MaintenanceStatus.CANCELLED
        request.cancelled_at = func.now()
        request.cancelled_by_user_id = actor.id
        request.cancel_reason = clean_reason
        after = {
            **_ids(request), "status": MaintenanceStatus.CANCELLED, "asset_status": asset.status,
            "reason": clean_reason,
        }
        _audit_and_commit(
            db, actor=actor, asset=asset, action=AuditAction.MAINTENANCE_STATUS_CHANGED,
            before=before, after=after, context=context,
        )
    except Exception:
        db.rollback()
        raise
    db.refresh(request)
    return request


def update_request(
    db: Session, *, actor: User, request: MaintenanceRequest, changes: dict[str, Any],
    context: AuditContext | None = None,
) -> MaintenanceRequest:
    """Edit priority, service provider, repair notes and cost while the request is open (S6, S9, S10,
    S12). Only what changes is saved and audited (maintenance.updated, old and new values); an edit
    that changes nothing writes nothing.

    Errors: 409 `maintenance_request_closed`; 422 `invalid_service_provider`, `invalid_repair_notes`."""
    try:
        asset, request = _lock_both(db, request)
        if not request.is_open:
            raise AppError(
                409, "maintenance_request_closed",
                f"{request.request_number} is {_STATUS_LABELS[request.status]} and cannot be changed any more.",
                {"status": request.status},
            )
        cleaned: dict[str, Any] = {}
        for field, value in changes.items():
            if field == "service_provider":
                value = _provider(value)
            elif field == "repair_notes":
                value = _clean(
                    value, max_length=REPAIR_NOTES_MAX_LENGTH, code="invalid_repair_notes", label="repair notes"
                )
            elif field == "cost":
                value = _money(value)
            cleaned[field] = value
        before: dict[str, Any] = {}
        after: dict[str, Any] = {}
        for field, value in cleaned.items():
            old = getattr(request, field)
            if old != value:
                before[field], after[field] = old, value
                setattr(request, field, value)
        if not after:
            db.rollback()  # nothing changed: nothing saved, no audit row (as B16)
            return get_request(db, request.id)
        _audit_and_commit(
            db, actor=actor, asset=asset, action=AuditAction.MAINTENANCE_UPDATED,
            before={**_ids(request), **before}, after={**_ids(request), **after}, context=context,
        )
    except Exception:
        db.rollback()
        raise
    db.refresh(request)
    return request


# ---- Completion inspection (Slice 6.3) -----------------------------------------------------------
_OUTCOME_LABELS = {
    InspectionOutcome.AVAILABLE: "Available",
    InspectionOutcome.DAMAGED: "Damaged",
    InspectionOutcome.RETIRED: "Retired",
}


def _ensure_awaiting_inspection(request: MaintenanceRequest) -> None:
    if request.awaiting_inspection:
        return
    number = request.request_number
    if request.inspected_at is not None:
        message = f"{number} has already been inspected. An inspection is final."
    elif request.status in MaintenanceStatus.OPEN:
        message = f"{number} is {_STATUS_LABELS[request.status]}. Mark the repair completed first."
    else:  # Cancelled before work started: the asset was never taken in for repair
        message = f"{number} was cancelled before work started, so there is nothing to inspect."
    raise AppError(409, "request_not_awaiting_inspection", message, {"status": request.status})


def _inspection_outcome(value: str | None) -> str:
    if value not in InspectionOutcome.ALL:
        raise AppError(
            422, "invalid_inspection_outcome", "Please choose the inspection outcome: Available, Damaged or Retired."
        )
    return value


def _condition_notes(outcome: str, value: str | None) -> str | None:
    """Same wording and limit as the return's condition notes (N4, K3); for Retired they are the
    retirement reason, so at most 500 (A3)."""
    notes = (value or "").strip() or None
    if notes is not None and len(notes) > INSPECTION_NOTES_MAX_LENGTH:
        raise AppError(
            422, "invalid_condition_notes",
            f"The condition notes can be at most {INSPECTION_NOTES_MAX_LENGTH:,} characters.",
        )
    if notes is None and outcome != InspectionOutcome.AVAILABLE:
        raise AppError(
            422, "condition_notes_required",
            f"Please describe the condition: notes are required when the outcome is {_OUTCOME_LABELS[outcome]}.",
        )
    if outcome == InspectionOutcome.RETIRED and len(notes) > RETIRE_REASON_MAX_LENGTH:
        raise AppError(
            422, "invalid_retire_reason",
            f"For Retired the notes are the reason for retiring and can be at most {RETIRE_REASON_MAX_LENGTH} characters.",
        )
    return notes


def _earliest_inspection_date(request: MaintenanceRequest) -> date:
    """The completion date; for a request cancelled during repair, the day it was cancelled."""
    if request.completion_date is not None:
        return request.completion_date
    return request.cancelled_at.astimezone(_company_tz()).date()


def _inspection_date(request: MaintenanceRequest, value: date | None) -> date:
    today = _today()
    on = value or today
    if on > today:
        raise AppError(422, "inspection_date_in_future", "The inspection date cannot be in the future.")
    earliest = _earliest_inspection_date(request)
    if on < earliest:
        when = "the repair was completed" if request.completion_date is not None else "the request was cancelled"
        raise AppError(
            422, "inspection_date_before_completion",
            f"The inspection date cannot be before {when} ({earliest.isoformat()}).",
            {"earliest_date": earliest.isoformat()},
        )
    return on


def inspect_request(
    db: Session, *, actor: User, request: MaintenanceRequest, inspection_outcome: str | None,
    inspection_date: date | None = None, condition_notes: str | None = None,
    context: AuditContext | None = None,
) -> MaintenanceRequest:
    """Record the inspection after a repair (MNT-07, workflow 7.4). The outcome becomes the asset's
    status: Available (can be assigned again), Damaged, or Retired (permanent; the retirement record
    and asset.retired are written as for Retire...). Once and final. One transaction.

    Errors: 409 `request_not_awaiting_inspection`, `asset_not_under_maintenance`; 422
    `invalid_inspection_outcome`, `condition_notes_required`, `invalid_condition_notes`,
    `invalid_retire_reason`, `inspection_date_in_future`, `inspection_date_before_completion`."""
    try:
        asset, request = _lock_both(db, request)
        _ensure_awaiting_inspection(request)
        if asset.status != AssetStatus.UNDER_MAINTENANCE:
            raise AppError(
                409, "asset_not_under_maintenance",
                f"{asset.asset_code} is no longer Under Maintenance, so it cannot be inspected here.",
                {"status": asset.status},
            )
        outcome = _inspection_outcome(inspection_outcome)
        notes = _condition_notes(outcome, condition_notes)
        on = _inspection_date(request, inspection_date)

        before = {**_ids(request), "status": request.status, "asset_status": asset.status}
        request.inspection_outcome = outcome
        request.inspection_date = on
        request.inspection_notes = notes
        request.inspected_at = func.now()  # database time, like the audit row
        request.inspected_by_user_id = actor.id
        asset.status = outcome  # the outcome values are asset statuses
        if outcome == InspectionOutcome.RETIRED:
            asset.retired_by_user_id = actor.id
            asset.retired_at = func.now()
            asset.retire_reason = notes
        after = {
            **_ids(request), "status": request.status, "asset_status": asset.status,
            "inspection_outcome": outcome, "inspection_date": on, "condition_notes": notes,
        }
        audit.record(
            db, actor=actor, action=AuditAction.MAINTENANCE_INSPECTED, entity=asset,
            before=before, after=after, context=context,
        )
        if outcome == InspectionOutcome.RETIRED:
            audit.record(
                db, actor=actor, action=AuditAction.ASSET_RETIRED, entity=asset,
                before={"status": AssetStatus.UNDER_MAINTENANCE},
                after={"status": AssetStatus.RETIRED, "reason": notes, **_ids(request)},
                context=context,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(request)
    return request
