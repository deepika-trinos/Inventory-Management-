"""Asset endpoints: /api/v1/assets/... (Slice 3.2; asset register Slice 4.1).

ADMIN AND IT MANAGER ONLY: an Employee gets 403. (Employees see their own assigned
assets on "My Assets", Slice 6.4.)

Reading only: the asset register (list with search and filters), the locations in
use, one asset, and its history. Edit and retire are Slice 4.2. There is
deliberately NO delete endpoint (BR-12).
"""

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.core.pagination import PageParams, page_params
from app.modules.assets import service
from app.modules.assets.schemas import (
    AssetHistoryPage,
    AssetPage,
    AssetPurchaseSummary,
    AssetRead,
    AssetStatusField,
)
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import RoleName

router = APIRouter(
    prefix="/assets",
    tags=["assets"],
    dependencies=[Depends(require_roles(RoleName.ADMIN, RoleName.IT_MANAGER))],
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
    db: Session = Depends(get_db),
) -> dict:
    """Paged list (AST-03, AST-05). Filters combine. Sort by `asset_code`, `name`,
    `category`, `brand`, `model`, `serial_number`, `status`, `location`,
    `warranty_expiry` or `created_at` (prefix `-` for descending); default: newest
    asset ID first.

    - Unknown `category_id`: **404** `category_not_found`
    - Unknown `status` or sort field: **422** `validation_error` / **400** `invalid_sort`
    """
    return service.list_assets(db, params, search=search, category_id=category_id, status=status_filter, location=location)


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
    asset = service.get_asset(db, asset_ref)
    summary = service.purchase_summary(asset)
    return AssetRead.model_validate(asset).model_copy(
        update={"purchase": AssetPurchaseSummary(**summary) if summary else None}
    )
