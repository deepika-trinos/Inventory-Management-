"""Application entry point.

Run it with:  uvicorn app.main:app --reload
This file creates the FastAPI app, sets up CORS, and plugs in each module's routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.modules.health.routes import router as health_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for the IT Asset & Inventory Management System.",
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

app.include_router(health_router)
