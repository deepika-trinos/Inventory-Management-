"""Admin-only endpoints: /api/v1/admin/..."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.errors import error_responses
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import RoleName, User

router = APIRouter(prefix="/admin", tags=["admin"])


class PingResponse(BaseModel):
    message: str
    email: str
    role: str


@router.get(
    "/ping",
    response_model=PingResponse,
    summary="Admin-only test endpoint",
    responses=error_responses(401, 403),
)
def ping(user: User = Depends(require_roles(RoleName.ADMIN))) -> PingResponse:
    """Answers only for Admins. Proves server-side role checks work.

    - No token: **401** `not_authenticated`
    - IT Manager or Employee token: **403** `forbidden`
    """
    return PingResponse(message="pong", email=user.email, role=user.role.name)
