"""Shared helpers for the account scripts: ask for email/password safely."""

import getpass
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BACKEND_DIR


class SeedSettings(BaseSettings):
    """Optional ADMIN_EMAIL / ADMIN_PASSWORD from the environment or backend/.env."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    admin_email: str | None = None
    admin_password: str | None = None


def ask_email(prompt: str = "Email: ") -> str:
    email = input(prompt).strip()
    if not email:
        sys.exit("No email entered. Nothing was created.")
    return email


def ask_password() -> str:
    """Ask twice without showing the characters on screen."""
    password = getpass.getpass("Password (not shown): ")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match. Nothing was created.")
    return password
