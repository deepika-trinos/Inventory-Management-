"""Maintenance request endpoints (Slice 6.1: MNT-01 to MNT-03; owner's answers Q9, Q10, Q13, O1-O14;
decisions M2, M3, M7 in decisions.md section 32).

- POST /assets/{ref}/maintenance-requests : staff report a problem with any asset (MNT-02)
- GET  /assets/{ref}/maintenance-requests : the asset's requests, newest first (staff)
- GET  /maintenance-requests              : every request, paged (staff; the Maintenance page)
- POST /me/maintenance-requests           : an Employee reports a problem with an asset they hold (MNT-01)

Staff = Admin and IT Manager (Q13: no technician role). Reporting never changes the asset's status (Q9).
"""

from fastapi import APIRouter, Depends, Query, status
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
    MaintenanceReport,
    MaintenanceRequestPage,
    MaintenanceRequestRead,
    MaintenanceStatusField,
    MyMaintenanceReport,
    MyMaintenanceRequestRead,
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
    status_filter: MaintenanceStatusField | None = Query(None, alias="status", description="Only this status."),
    db: Session = Depends(get_db),
) -> dict:
    """Every maintenance request, newest first (O12). Sort by `request_number`, `reported_date`,
    `priority`, `status` or `asset_code` (prefix `-` for descending). Unknown status:
    **422** `validation_error`; unknown sort field: **400** `invalid_sort`."""
    page = service.list_requests(db, params, search=search, status=status_filter)
    page["items"] = [_read(r) for r in page["items"]]
    return page


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
