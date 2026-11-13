"""Asset endpoints: /api/v1/assets/... (Slice 3.2).

ADMIN AND IT MANAGER ONLY: an Employee gets 403. (Employees see their own assigned
assets on "My Assets", Slice 6.4.)

Only "get one asset" exists for now, so a received purchase can link to the
assets it created. The asset register (list, search, filters) is Slice 4.1;
edit and retire are Slice 4.2. There is deliberately NO delete endpoint (BR-12).
"""

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import error_responses
from app.modules.assets import service
from app.modules.assets.schemas import AssetPurchaseSummary, AssetRead
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import RoleName

router = APIRouter(
    prefix="/assets",
    tags=["assets"],
    dependencies=[Depends(require_roles(RoleName.ADMIN, RoleName.IT_MANAGER))],
    responses=error_responses(401, 403),
)


@router.get("/{asset_ref}", response_model=AssetRead, summary="Get one asset", responses=error_responses(404))
def get_asset(
    asset_ref: str = Path(max_length=30, description='The asset\'s id (e.g. 7) or asset ID (e.g. "AST-000007").'),
    db: Session = Depends(get_db),
) -> AssetRead:
    """One asset by id or asset ID, with where it came from (purchase number, vendor,
    invoice / reference). Unknown: **404** `asset_not_found`."""
    asset = service.get_asset(db, asset_ref)
    summary = service.purchase_summary(asset)
    return AssetRead.model_validate(asset).model_copy(
        update={"purchase": AssetPurchaseSummary(**summary) if summary else None}
    )
