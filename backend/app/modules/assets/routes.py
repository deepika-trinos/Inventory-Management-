"""Asset endpoints: /api/v1/assets/... (Slice 3.2; asset register Slice 4.1).

ADMIN AND IT MANAGER ONLY: an Employee gets 403. (Employees see their own assigned
assets on "My Assets", Slice 6.4.)

The asset register (list with search and filters), the locations in use, one
asset and its history (Slice 4.1); editing the allowed details and retiring
(Slice 4.2); assigning to an employee (Slice 5.1) and returning it (Slice 5.2).
There is deliberately NO delete endpoint (BR-12).
"""

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.core.pagination import PageParams, page_params
from app.modules.assets import service
from app.modules.assets.models import Asset
from app.modules.assets.schemas import (
    AssetAssign,
    AssetCreate,
    AssetCurrentAssignment,
    AssetEmployeeSummary,
    AssetHistoryPage,
    AssetListItem,
    AssetPage,
    AssetPurchaseSummary,
    AssetRead,
    AssetRetire,
    AssetReturn,
    AssetStatusField,
    AssetUpdate,
)
from app.modules.assignments import service as assignments_service
from app.modules.audit.service import AuditContext, get_audit_context
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import RoleName, User

require_staff = require_roles(RoleName.ADMIN, RoleName.IT_MANAGER)

router = APIRouter(
    prefix="/assets",
    tags=["assets"],
    dependencies=[Depends(require_staff)],
    responses=error_responses(401, 403),
)


AssetRef = Path(max_length=30, description="The asset's id (e.g. 7) or asset ID (e.g. \"AST-000007\").")


@router.get("", response_model=AssetPage, summary="List assets (asset register)", responses=error_responses(404))
def list_assets(
    params: PageParams = Depends(page_params),
    search: str | None = Query(None, max_length=100, description="Part of an asset ID, serial number or name (any case)."),
    category_id: int | None = Query(None, ge=1, description="Only assets of this category."),
    status_filter: AssetStatusField | None = Query(None, alias="status", description="Only assets with this status."),
    location: str | None = Query(None, max_length=200, description="Exact location (any case)."),
    assigned_to: int | None = Query(
        None, ge=1, description="Only assets this employee (active or inactive) holds now (Slice 5.1, A1)."
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Paged list (AST-03, AST-05). Filters combine. Sort by `asset_code`, `name`,
    `category`, `brand`, `model`, `serial_number`, `status`, `location`,
    `warranty_expiry` or `created_at` (prefix `-` for descending); default: newest
    asset ID first.

    Each row carries `assigned_to`: the employee holding it now (empty unless Assigned).

    - Unknown `category_id`: **404** `category_not_found`; unknown `assigned_to`: **404** `employee_not_found`
    - Unknown `status` or sort field: **422** `validation_error` / **400** `invalid_sort`
    """
    page = service.list_assets(
        db, params, search=search, category_id=category_id, status=status_filter, location=location,
        assigned_to=assigned_to,
    )
    holders = assignments_service.open_assignments_for_assets(db, [a.id for a in page["items"]])
    page["items"] = [
        AssetListItem.model_validate(asset).model_copy(
            update={
                "assigned_to": AssetEmployeeSummary.model_validate(holders[asset.id].employee)
                if asset.id in holders else None
            }
        )
        for asset in page["items"]
    ]
    return page


@router.post(
    "", response_model=AssetRead, status_code=status.HTTP_201_CREATED,
    summary="Enter an existing asset (no purchase)", responses=error_responses(404, 409, 422),
)
def create_asset(
    body: AssetCreate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> AssetRead:
    """Manual entry of equipment the company already owns (Slice 4.5, AST-01, Q4; owner's
    answer A7). Same asset ID sequence and serial check as receiving; status Available;
    no purchase link or vendor. Writes audit `asset.created` in the same transaction.

    - Unknown category: **404** `category_not_found`; inactive: **409** `category_inactive`;
      tracked by quantity: **409** `category_not_serialized`
    - Serial used by another asset (any case): **409** `serial_number_taken`
    - Missing serial / model / name, too long: **422** `invalid_*`
    - Purchase date in the future: **422** `purchase_date_in_future`;
      warranty before the purchase date: **422** `invalid_warranty_expiry`"""
    asset = service.create_asset(db, actor=user, data=body.model_dump(), context=context)
    return _read(asset, db)


@router.get("/locations", response_model=list[str], summary="Locations in use")
def list_locations(db: Session = Depends(get_db)) -> list[str]:
    """Every location already typed on an asset, A-Z (for the location filter)."""
    return service.list_locations(db)


@router.get(
    "/{asset_ref}/history", response_model=AssetHistoryPage, summary="An asset's history", responses=error_responses(404)
)
def asset_history(
    asset_ref: str = AssetRef,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
) -> dict:
    """Every audit log entry about this asset, newest first, with who did it.
    Unknown asset: **404** `asset_not_found`."""
    asset = service.get_asset(db, asset_ref)
    return service.asset_history(db, asset, params)


@router.get("/{asset_ref}", response_model=AssetRead, summary="Get one asset", responses=error_responses(404))
def get_asset(
    asset_ref: str = Path(max_length=30, description='The asset\'s id (e.g. 7) or asset ID (e.g. "AST-000007").'),
    db: Session = Depends(get_db),
) -> AssetRead:
    """One asset by id or asset ID, with where it came from (purchase number, vendor,
    invoice / reference; empty for manual entry) and who created it, and when.
    Unknown: **404** `asset_not_found`."""
    return _read(service.get_asset(db, asset_ref), db)


def _read(asset: Asset, db: Session) -> AssetRead:
    """One asset as the API returns it, with where it came from and who holds it now."""
    summary = service.purchase_summary(asset)
    current = assignments_service.summary(assignments_service.open_assignment(db, asset.id))
    return AssetRead.model_validate(asset).model_copy(
        update={
            "purchase": AssetPurchaseSummary(**summary) if summary else None,
            "current_assignment": AssetCurrentAssignment.model_validate(current) if current else None,
        }
    )


@router.patch(
    "/{asset_ref}", response_model=AssetRead, summary="Edit an asset", responses=error_responses(404, 409, 422)
)
def update_asset(
    body: AssetUpdate,
    asset_ref: str = AssetRef,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> AssetRead:
    """Change the editable details (owner's answer A2): name, brand, model, serial
    number, location, warranty expiry; on assets entered by hand also category,
    purchase date and cost (Slice 4.5, I4). Send only what changes; `null` clears an
    optional field.

    - Status or any other field: **422** `validation_error`
    - Category, purchase date or cost on a received asset: **422** `validation_error`
      (`details.field`); category not an active one-by-one category: as on entry
    - Retired asset: **409** `asset_retired`
    - Serial number used by another asset (any case): **409** `serial_number_taken`
    - Empty name / model / serial, too long, warranty before the purchase date: **422** `invalid_*`
    - Writes audit action `asset.updated` (old and new value of each changed field)."""
    asset = service.get_asset(db, asset_ref)
    changes = body.model_dump(exclude_unset=True)  # only what was actually sent
    return _read(service.update_asset(db, actor=user, asset=asset, changes=changes, context=context), db)


@router.post(
    "/{asset_ref}/retire", response_model=AssetRead, summary="Retire an asset",
    responses=error_responses(404, 409, 422),
)
def retire_asset(
    body: AssetRetire,
    asset_ref: str = AssetRef,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> AssetRead:
    """Retire the asset permanently (owner's answer A3). Cannot be undone; a retired
    asset can no longer be edited.

    - Only from Available or Damaged; Assigned or Under Maintenance: **409** `asset_not_retirable`
    - Already retired: **409** `asset_retired`
    - An open maintenance request: **409** `asset_has_open_request` (`details.request_number`; Slice 6.2, S14)
    - Missing or too long reason (max 500): **422** `invalid_retire_reason`
    - Writes audit action `asset.retired` with the reason."""
    asset = service.get_asset(db, asset_ref)
    return _read(service.retire_asset(db, actor=user, asset=asset, reason=body.reason, context=context), db)


@router.post(
    "/{asset_ref}/assign", response_model=AssetRead, summary="Assign an asset to an employee",
    responses=error_responses(404, 409, 422),
)
def assign_asset(
    body: AssetAssign,
    asset_ref: str = AssetRef,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> AssetRead:
    """Give an Available asset to an active employee (Slice 5.1: ASN-01 to ASN-04, EMP-05,
    BR-02, BR-03, BR-05, BR-11; owner's answers N1-N3, N9). The asset becomes Assigned.
    One transaction with audit `assignment.created`; a failure saves nothing.

    - Asset not Available: **409** `asset_already_assigned`, `asset_under_maintenance`,
      `asset_damaged` or `asset_retired` (`details.status`)
    - Unknown employee: **404** `employee_not_found`; deactivated: **409** `employee_inactive`
    - Assignment date in the future: **422** `assignment_date_in_future`; before the asset
      was created: **422** `assignment_date_before_asset_created`
    - Expected return date before the assignment date: **422** `invalid_expected_return_date`
    - Returns the asset with its `current_assignment`."""
    asset = service.get_asset(db, asset_ref)
    assignments_service.assign_asset(
        db, actor=user, asset=asset, employee_id=body.employee_id,
        assignment_date=body.assignment_date, expected_return_date=body.expected_return_date, context=context,
    )
    return _read(service.get_asset(db, asset.id), db)


@router.post(
    "/{asset_ref}/return", response_model=AssetRead, summary="Return an asset (with inspection)",
    responses=error_responses(404, 409, 422),
)
def return_asset(
    body: AssetReturn,
    asset_ref: str = AssetRef,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> AssetRead:
    """Record the return and the inspection on the same form (Slice 5.2: ASN-05, ASN-06,
    BR-04; owner's answers Q5, N4, N5, N9). Closes the open assignment (kept with its return
    details) and sets the asset's status from the outcome. Under Maintenance sets the
    status only: no maintenance request is created (N5). One transaction with audit
    `assignment.returned`; a failure saves nothing.

    - Asset not assigned: **409** `asset_not_assigned` (`details.status`)
    - Outcome missing or unknown: **422** `invalid_inspection_outcome`
    - Notes missing for Under Maintenance or Damaged: **422** `condition_notes_required`;
      over 1,000 characters: **422** `invalid_condition_notes`
    - Return date in the future: **422** `return_date_in_future`; before the assignment
      date: **422** `return_date_before_assignment`
    - Returns the asset with its new status and no `current_assignment`."""
    asset = service.get_asset(db, asset_ref)
    assignments_service.return_asset(
        db, actor=user, asset=asset, inspection_outcome=body.inspection_outcome,
        return_date=body.return_date, condition_notes=body.condition_notes, context=context,
    )
    return _read(service.get_asset(db, asset.id), db)
