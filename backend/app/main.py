"""Application entry point.

Run it with:  uvicorn app.main:app --reload
This file creates the FastAPI app, sets up CORS and the shared error format,
and plugs in each module's routes.
"""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.modules.admin.routes import router as admin_router
from app.modules.auth.routes import router as auth_router
from app.modules.categories.routes import router as categories_router
from app.modules.health.routes import router as health_router
from app.modules.users.routes import router as users_router

settings = get_settings()

API_PREFIX = "/api/v1"

DESCRIPTION = """
Backend API for the IT Asset & Inventory Management System.

**How to try protected endpoints here:**
1. Open `POST /api/v1/auth/login`, click *Try it out*, enter email and password, *Execute*.
2. Copy the `access_token` from the response.
3. Click **Authorize** (top right), paste the token, *Authorize*.

**Errors** always look like `{"error": {"code": "...", "message": "...", "details": ...}}`.

**Times** are stored and returned in UTC; screens show them in the company timezone.
"""

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=DESCRIPTION,
    openapi_tags=[
        {"name": "auth", "description": "Log in, current user, log out."},
        {"name": "users", "description": "User management (Admin only)."},
        {"name": "categories", "description": "Asset categories (Admin and IT Manager). Never deleted, only deactivated."},
        {"name": "admin", "description": "Admin-only endpoints."},
        {"name": "health", "description": "Is the API and database working?"},
    ],
)

# CORS: browsers block a page on one address (the React app, :5173) from calling
# an API on another address (:8000) unless the API lists that page's address here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(health_router)

api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(users_router)
api_router.include_router(categories_router)
app.include_router(api_router)
