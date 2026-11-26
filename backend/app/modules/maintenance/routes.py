"""Maintenance request endpoints (Slice 6.1: MNT-01 to MNT-03; owner's answers Q9, Q10, Q13, O1-O14;
decisions M2, M3, M7 in decisions.md section 32).

- POST /assets/{ref}/maintenance-requests : staff report a problem with any asset (MNT-02)
- GET  /assets/{ref}/maintenance-requests : the asset's requests, newest first (staff)
- GET  /maintenance-requests              : every request, paged (staff; the Maintenance page)
- POST /me/maintenance-requests           : an Employee reports a problem with an asset they hold (MNT-01)

Slice 6.2 (MNT-04 to MNT-07; owner's answers S1-S14; decisions U2-U6), staff only:
- GET   /maintenance-requests/{ref}           : one request with its history
- POST  /maintenance-requests/{ref}/start     : Reported -> In Progress (asset Under Maintenance)
- POST  /maintenance-requests/{ref}/complete  : In Progress -> Completed (asset stays Under Maintenance)
- POST  /maintenance-requests/{ref}/cancel    : Reported or In Progress -> Cancelled
- PATCH /maintenance-requests/{ref}           : priority and details while open

Slice 6.3 (MNT-07, workflow 7.4; decisions.md section 35), staff only:
- POST  /maintenance-requests/{ref}/inspect   : the inspection after the repair (asset Available,
                                                Damaged or Retired)

Slice 6.4 (MNT-08; decisions.md section 37), Employee only:
- GET   /me/maintenance-requests             : the requests I reported, newest first (Employee-safe fields)

Staff = Admin and IT Manager (Q13: no technician role). Reporting never changes the asset's status (Q9).
"""

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.core.pagination import PageParams, page_params
from app.modules.assets import service as assets_service
from app.modules.assets.routes import AssetRef
from app.modules.assignments import service as assignments_service
from app.modules.audit.service import AuditContext, get_audit_context
from app.modules.auth.dependencies import require_roles
from app.modules.maintenance import service
from app.modules.maintenance.schemas import (
    MaintenanceCancel,
    MaintenanceComplete,
    MaintenanceInspect,
    MaintenanceReport,
    MaintenanceRequestDetail,
    MaintenanceRequestPage,
    MaintenanceRequestRead,
    MaintenanceStart,
    MaintenanceStatusFilter,
    MaintenanceUpdate,
    MyMaintenanceReport,
    MyMaintenanceRequestRead,
    MyRequestRow,
)
from app.modules.users.models import RoleName, User

require_staff = require_roles(RoleName.ADMIN, RoleName.IT_MANAGER)
require_employee = require_roles(RoleName.EMPLOYEE)

router = APIRouter(
    prefix="/maintenance-requests", tags=["maintenance"], dependencies=[Depends(require_staff)],
    responses=error_responses(401, 403),
)
asset_router = APIRouter(
    prefix="/assets", tags=["maintenance"], dependencies=[Depends(require_staff)],
    responses=error_responses(401, 403),
)
me_router = APIRouter(prefix="/me", tags=["maintenance"], responses=error_responses(401, 403))


def _read(request) -> MaintenanceRequestRead:
    return MaintenanceRequestRead.model_validate(service.read(request))


@router.get("", response_model=MaintenanceRequestPage, summary="List maintenance requests")
def list_requests(
    params: PageParams = Depends(page_params),
    search: str | None = Query(
        None, max_length=100, description="Part of the request number, asset ID, asset name or serial number."
    ),
    status_filter: MaintenanceStatusFilter | None = Query(
        None, alias="status", description='Only this status, or "awaiting_inspection" (Slice 6.3).'
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Every maintenance request, newest first (O12). Sort by `request_number`, `reported_date`,
    `priority`, `status` or `asset_code` (prefix `-` for descending). Unknown status:
    **422** `validation_error`; unknown sort field: **400** `invalid_sort`."""
    page = service.list_requests(db, params, search=search, status=status_filter)
    page["items"] = [_read(r) for r in page["items"]]
    return page


RequestRef = Path(max_length=30, description='The request\'s id (e.g. 5) or number (e.g. "MNT-000005").')


def _detail(db: Session, request) -> MaintenanceRequestDetail:
    return MaintenanceRequestDetail.model_validate(
        {**service.read(request), "history": service.request_history(db, request)}
    )


@router.get(
    "/{request_ref}", response_model=MaintenanceRequestDetail, summary="Get one maintenance request",
    responses=error_responses(404),
)
def get_request(request_ref: str = RequestRef, db: Session = Depends(get_db)) -> MaintenanceRequestDetail:
    """One request with its progress and its history, newest first (Slice 6.2, U2, S13).
    Unknown: **404** `maintenance_request_not_found`."""
    return _detail(db, service.get_request(db, request_ref))


@router.post(
    "/{request_ref}/start", response_model=MaintenanceRequestDetail, summary="Start work (Reported -> In Progress)",
    responses=error_responses(404, 409, 422),
)
def start_work(
    body: MaintenanceStart,
    request_ref: str = RequestRef,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> MaintenanceRequestDetail:
    """The asset becomes **Under Maintenance** and cannot be assigned (Q9, BR-05). One transaction with
    audit `maintenance.status_changed`.

    - Not Reported: **409** `invalid_status_change` (`details.from`, `details.to`)
    - Asset Assigned: **409** `asset_assigned` (return it first, S1); Retired: **409** `asset_retired`
    - Start date in the future: **422** `started_date_in_future`; before the reported date:
      **422** `started_date_before_reported`
    - Service provider over 200 characters: **422** `invalid_service_provider`"""
    request = service.get_request(db, request_ref)
    saved = service.start_work(
        db, actor=user, request=request, started_date=body.started_date,
        service_provider=body.service_provider, context=context,
    )
    return _detail(db, saved)


@router.post(
    "/{request_ref}/complete", response_model=MaintenanceRequestDetail,
    summary="Mark completed (In Progress -> Completed)", responses=error_responses(404, 409, 422),
)
def complete_work(
    body: MaintenanceComplete,
    request_ref: str = RequestRef,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> MaintenanceRequestDetail:
    """Records the repair (MNT-05). The asset **stays Under Maintenance** until it is inspected
    (Slice 6.3, MNT-07). One transaction with audit `maintenance.status_changed`.

    - Not In Progress: **409** `invalid_status_change`
    - Repair notes missing, blank or over 1,000: **422** `invalid_repair_notes`
    - Completion date in the future: **422** `completion_date_in_future`; before the start date:
      **422** `completion_date_before_start`
    - Cost below 0 or more than 2 decimals: **422** `validation_error`"""
    request = service.get_request(db, request_ref)
    saved = service.complete_work(
        db, actor=user, request=request, repair_notes=body.repair_notes, completion_date=body.completion_date,
        service_provider=body.service_provider, cost=body.cost, context=context,
    )
    return _detail(db, saved)


@router.post(
    "/{request_ref}/cancel", response_model=MaintenanceRequestDetail, summary="Cancel a request",
    responses=error_responses(404, 409, 422),
)
def cancel_request(
    body: MaintenanceCancel,
    request_ref: str = RequestRef,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> MaintenanceRequestDetail:
    """From Reported (asset unchanged) or In Progress (asset stays Under Maintenance until inspected,
    S2). Final. One transaction with audit `maintenance.status_changed`.

    - Completed or Cancelled: **409** `invalid_status_change`
    - Reason missing, blank or over 500: **422** `invalid_cancel_reason`"""
    request = service.get_request(db, request_ref)
    return _detail(db, service.cancel_request(db, actor=user, request=request, reason=body.reason, context=context))


@router.post(
    "/{request_ref}/inspect", response_model=MaintenanceRequestDetail, summary="Inspect the asset after the repair",
    responses=error_responses(404, 409, 422),
)
def inspect_request(
    body: MaintenanceInspect,
    request_ref: str = RequestRef,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> MaintenanceRequestDetail:
    """For a request that is Completed, or Cancelled after work started (MNT-07). The outcome becomes the
    asset's status: **available**, **damaged** or **retired** (permanent; the asset's retirement record
    and `asset.retired` are written too). Once and final. One transaction with audit `maintenance.inspected`.

    - Not awaiting inspection (Reported, In Progress, cancelled before work started, already inspected):
      **409** `request_not_awaiting_inspection` (`details.status`)
    - The asset is not Under Maintenance: **409** `asset_not_under_maintenance`
    - Outcome missing or not one of the three: **422** `invalid_inspection_outcome`
    - Notes over 1,000: **422** `invalid_condition_notes`; missing for Damaged or Retired: **422**
      `condition_notes_required`; over 500 for Retired: **422** `invalid_retire_reason`
    - Date in the future: **422** `inspection_date_in_future`; before the completion date (or the day it was
      cancelled): **422** `inspection_date_before_completion` (`details.earliest_date`)"""
    request = service.get_request(db, request_ref)
    saved = service.inspect_request(
        db, actor=user, request=request, inspection_outcome=body.inspection_outcome,
        inspection_date=body.inspection_date, condition_notes=body.condition_notes, context=context,
    )
    return _detail(db, saved)


@router.patch(
    "/{request_ref}", response_model=MaintenanceRequestDetail, summary="Edit a request's priority and details",
    responses=error_responses(404, 409, 422),
)
def update_request(
    body: MaintenanceUpdate,
    request_ref: str = RequestRef,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> MaintenanceRequestDetail:
    """Change `priority`, `service_provider`, `repair_notes` or `cost` while the request is Reported or
    In Progress (S6, S9, S10, S12). Send only what changes; `null` clears. Audit `maintenance.updated`
    with the old and new values; an edit that changes nothing saves nothing.

    - Completed or Cancelled: **409** `maintenance_request_closed`
    - Too long: **422** `invalid_service_provider` / `invalid_repair_notes`; bad priority or cost, or any
      other field: **422** `validation_error`"""
    request = service.get_request(db, request_ref)
    changes = body.model_dump(exclude_unset=True)
    return _detail(db, service.update_request(db, actor=user, request=request, changes=changes, context=context))


@asset_router.get(
    "/{asset_ref}/maintenance-requests", response_model=list[MaintenanceRequestRead],
    summary="An asset's maintenance requests", responses=error_responses(404),
)
def asset_requests(asset_ref: str = AssetRef, db: Session = Depends(get_db)) -> list[MaintenanceRequestRead]:
    """Every request of this asset, newest first (O12, MNT-06 groundwork). Unknown asset: **404** `asset_not_found`."""
    asset = assets_service.get_asset(db, asset_ref)
    return [_read(r) for r in service.requests_for_asset(db, asset)]


@asset_router.post(
    "/{asset_ref}/maintenance-requests", response_model=MaintenanceRequestRead, status_code=status.HTTP_201_CREATED,
    summary="Report a problem with an asset", responses=error_responses(404, 409, 422),
)
def report_problem(
    body: MaintenanceReport,
    asset_ref: str = AssetRef,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> MaintenanceRequestRead:
    """Open a maintenance request with status Reported for any asset that is not retired
    (MNT-02, O1). The asset's status does not change (Q9). One transaction with audit
    `maintenance.reported`; a failure saves nothing.

    - Retired asset: **409** `asset_retired`
    - The asset already has an open request: **409** `maintenance_request_open` (`details.request_number`)
    - A request is awaiting inspection: **409** `maintenance_request_awaiting_inspection` (Slice 6.3)
    - Issue missing, blank or over 1,000 characters: **422** `invalid_issue_description`
    - Priority not low / medium / high, or any other field: **422** `validation_error`
    - Reported date in the future: **422** `reported_date_in_future`; before the asset was
      created: **422** `reported_date_before_asset_created`"""
    asset = assets_service.get_asset(db, asset_ref)
    request = service.report_problem(
        db, actor=user, asset=asset, issue_description=body.issue_description, priority=body.priority,
        reported_date=body.reported_date, context=context,
    )
    return _read(request)


@me_router.post(
    "/maintenance-requests", response_model=MyMaintenanceRequestRead, status_code=status.HTTP_201_CREATED,
    summary="Report a problem with my asset", responses=error_responses(404, 409, 422),
)
def report_my_problem(
    body: MyMaintenanceReport,
    user: User = Depends(require_employee),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> dict:
    """An Employee reports a problem with an asset they hold now (MNT-01, O3). Status Reported,
    reported date today, no priority (Q10, O5, O8). The asset's status does not change (Q9).
    Admin and IT Manager: 403 (they use the asset endpoint).

    - The asset is not held by you now (or does not exist): **404** `asset_not_found` (O7)
    - Login not linked to an employee record: **404** `employee_not_linked`
    - The asset already has an open request: **409** `maintenance_request_open`
    - Issue missing, blank or over 1,000 characters: **422** `invalid_issue_description`
    - A priority, a date or any other field: **422** `validation_error`"""
    employee = assignments_service.employee_of_login(db, user)
    asset = service.held_asset(db, employee, body.asset_id)
    request = service.report_problem(
        db, actor=user, asset=asset, issue_description=body.issue_description, holder=employee, context=context,
    )
    data = service.read(request)
    return {key: data[key] for key in ("request_number", "asset", "issue_description", "status", "reported_date")}


@me_router.get(
    "/maintenance-requests", response_model=list[MyRequestRow], summary="My maintenance requests",
)
def my_requests(user: User = Depends(require_employee), db: Session = Depends(get_db)) -> list[dict]:
    """The requests **you reported**, newest first, including those for assets you have since returned
    (MNT-08, O6). Requests staff created are not included. Only the number, asset, problem, status and the
    reported / work started / completed / cancelled dates and the cancel reason are returned; never the
    priority, service provider, repair notes, cost, staff e-mails or inspection details.
    Admin and IT Manager: **403** (they use `/maintenance-requests`)."""
    return [service.my_read(r) for r in service.my_requests(db, user)]
