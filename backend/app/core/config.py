"""Application settings.

All settings come from environment variables. During development they are read
from the file ``backend/.env`` (copied from ``.env.example``). A real
environment variable always wins over a value in ``.env``.

Nothing secret is written in this file; it only describes WHICH settings exist
and their safe defaults.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ folder (this file is backend/app/core/config.py)
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unrelated variables in .env
    )

    app_name: str = "IT Asset & Inventory Management API"
    app_env: Literal["development", "test", "production"] = "development"

    # Required: there is no safe default for the database address.
    database_url: str
    # Only needed when running pytest.
    test_database_url: str | None = None

    # Comma-separated list of browser origins allowed by CORS.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Dates are stored in UTC and displayed in this timezone (decision Q11).
    # The backend always stores and returns UTC; screens convert for display.
    app_timezone: str = "Asia/Kolkata"

    sql_echo: bool = False

    # ---- Login tokens (JWT) ----
    # Secret used to SIGN tokens. Anyone who knows it can forge a login, so it
    # must be long, random, different per environment and never committed.
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    # Short-lived tokens: after this many minutes the user must log in again.
    access_token_expire_minutes: int = Field(default=30, ge=1, le=24 * 60)

    # Minimum length for new passwords (seed script now; user management in Slice 1.6).
    password_min_length: int = Field(default=12, ge=8)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _check_production_safety(self) -> "Settings":
        """Stop the app from starting with development-only settings in production."""
        if self.is_production:
            if any("localhost" in o or "127.0.0.1" in o for o in self.cors_origin_list):
                raise ValueError("CORS_ORIGINS must not contain localhost in production.")
            if self.sql_echo:
                raise ValueError("SQL_ECHO must be false in production.")
            if "change-me" in self.jwt_secret_key:
                raise ValueError("JWT_SECRET_KEY must be a real random secret in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the settings, read once and then reused (cached)."""
    return Settings()
