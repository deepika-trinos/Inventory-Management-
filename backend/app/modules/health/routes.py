"""GET /health: is the API running, and can it reach the database?"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.health.schemas import HealthResponse
from app.modules.health.service import is_database_reachable

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database unreachable"}},
)
def health(response: Response, db: Session = Depends(get_db)) -> HealthResponse:
    """Return 200 when everything works, 503 (Service Unavailable) when the database is down."""
    if is_database_reachable(db):
        return HealthResponse(status="ok", database="reachable")
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="degraded", database="unreachable")
