"""Small shared helpers for cleaning typed-in text fields (employees, vendors, ...)."""

import re

from app.core.errors import AppError

# Phone: digits plus the usual separators (decision B22). Format is not checked further.
PHONE_RE = re.compile(r"^\+?[0-9 ()./-]{3,30}$")


def required_text(value: str, code: str, message: str) -> str:
    """Trimmed text that must not be empty (422 `code` otherwise)."""
    value = value.strip()
    if not value:
        raise AppError(422, code, message)
    return value


def optional_text(value: str | None) -> str | None:
    """Trimmed text; empty becomes None."""
    if value is None:
        return None
    return value.strip() or None


def clean_phone(value: str | None) -> str | None:
    """Optional phone number (B22): 422 `invalid_phone` when it has other characters."""
    value = optional_text(value)
    if value and not PHONE_RE.match(value):
        raise AppError(422, "invalid_phone", "Phone may contain digits, spaces, + ( ) . / and - only.")
    return value
