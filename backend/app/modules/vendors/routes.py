"""Vendor endpoints: /api/v1/vendors/... (Slice 2.3, VEN-01 to VEN-03, VEN-05).

ADMIN AND IT MANAGER ONLY: the whole router requires one of those roles
(checked on the server for every request), so an Employee gets 403 on all of these.

There is deliberately NO delete endpoint (BR-12, VEN-05): deactivate instead.
A vendor's purchase history (VEN-04) is added in Slice 3.4.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.core.pagination import PageParams, page_params
from app.modules.audit.service import AuditContext, get_audit_context
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import RoleName, User
from app.modules.vendors import service
from app.modules.vendors.models import Vendor
from app.modules.vendors.schemas import VendorCreate, VendorPage, VendorRead, VendorStatusField, VendorUpdate

require_staff = require_roles(RoleName.ADMIN, RoleName.IT_MANAGER)

router = APIRouter(
    prefix="/vendors",
    tags=["vendors"],
    dependencies=[Depends(require_staff)],  # every endpoint below: Admin or IT Manager
    responses=error_responses(401, 403),
)


@router.get("", response_model=VendorPage, summary="List vendors")
def list_vendors(
    params: PageParams = Depends(page_params),
    search: str | None = Query(
        None, max_length=100, description="Part of the name, contact person, email or phone."
    ),
    status_filter: VendorStatusField | None = Query(None, alias="status", description="Only active or inactive."),
    db: Session = Depends(get_db),
) -> dict:
    """Paged list. Sort by `name`, `contact_person`, `email`, `status`,
    `created_at` or `updated_at` (prefix `-` for descending)."""
    return service.list_vendors(db, params, search=search, status=status_filter)


@router.post(
    "",
    response_model=VendorRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a vendor",
    responses=error_responses(409, 422),
)
def create_vendor(
    body: VendorCreate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Vendor:
    """Create an active vendor. Only the name is required.

    - Duplicate name (any upper/lower case): **409** `vendor_name_taken`
    - Blank name / bad email / bad phone: **422** `invalid_name` / `invalid_email` / `invalid_phone`
    - Writes audit action `vendor.created`.
    """
    return service.create_vendor(db, data=body.model_dump(), actor=user, context=context)


@router.get("/{vendor_id}", response_model=VendorRead, summary="Get one vendor", responses=error_responses(404))
def get_vendor(vendor_id: int, db: Session = Depends(get_db)) -> Vendor:
    return service.get_vendor(db, vendor_id)


@router.patch(
    "/{vendor_id}",
    response_model=VendorRead,
    summary="Edit a vendor",
    responses=error_responses(404, 409, 422),
)
def update_vendor(
    vendor_id: int,
    body: VendorUpdate,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Vendor:
    """Send only the fields to change; `null` clears an optional field.
    Writes audit action `vendor.updated` when something changed."""
    vendor = service.get_vendor(db, vendor_id)
    changes = body.model_dump(exclude_unset=True)  # only what was actually sent
    return service.update_vendor(db, actor=user, vendor=vendor, changes=changes, context=context)


@router.post(
    "/{vendor_id}/activate",
    response_model=VendorRead,
    summary="Activate a vendor",
    responses=error_responses(404),
)
def activate_vendor(
    vendor_id: int,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Vendor:
    """Allow new purchases from this vendor again. Writes audit action `vendor.activated`."""
    vendor = service.get_vendor(db, vendor_id)
    return service.set_active(db, actor=user, vendor=vendor, active=True, context=context)


@router.post(
    "/{vendor_id}/deactivate",
    response_model=VendorRead,
    summary="Deactivate a vendor",
    responses=error_responses(404),
)
def deactivate_vendor(
    vendor_id: int,
    user: User = Depends(require_staff),
    context: AuditContext = Depends(get_audit_context),
    db: Session = Depends(get_db),
) -> Vendor:
    """Stop new purchases from this vendor (never deletes it, BR-12 / VEN-05). It
    stays readable and existing purchases keep it. Writes audit action `vendor.deactivated`."""
    vendor = service.get_vendor(db, vendor_id)
    return service.set_active(db, actor=user, vendor=vendor, active=False, context=context)
