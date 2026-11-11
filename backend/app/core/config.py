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

from pydantic import model_validator
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
    app_timezone: str = "Asia/Kolkata"

    sql_echo: bool = False

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
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the settings, read once and then reused (cached)."""
    return Settings()
