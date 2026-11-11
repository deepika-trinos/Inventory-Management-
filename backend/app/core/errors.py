"""One error format for the whole API.

Every error response looks like this, whatever went wrong:

    {
      "error": {
        "code": "validation_error",          # short, stable, for the frontend's code
        "message": "Some fields are invalid.", # readable sentence for people
        "details": [...] or {...} or null     # extra information, if any
      }
    }

How to raise an error from any service or route:

    raise AppError(404, "not_found", "Asset not found.")
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# ---- Schemas (used in the Swagger docs) -------------------------------------
class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


# Reusable "responses=" entries for route decorators, so /docs shows the errors.
def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    descriptions = {
        400: "Bad request",
        401: "Not logged in, or the token is invalid/expired",
        403: "Logged in, but your role is not allowed to do this",
        404: "Not found",
        409: "Conflict with existing data",
        422: "Some request fields are invalid",
    }
    return {
        code: {"model": ErrorResponse, "description": descriptions.get(code, "Error")}
        for code in status_codes
    }


# ---- The exception our own code raises --------------------------------------
class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


_DEFAULT_CODES = {
    400: "bad_request",
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "too_many_requests",
}


def _error_json(
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=body.model_dump(), headers=headers)


# ---- Handlers: turn every kind of error into the format above ---------------
async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return _error_json(exc.status_code, exc.code, exc.message, exc.details, exc.headers)


async def _http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Errors raised by FastAPI itself (e.g. unknown address -> 404).
    code = _DEFAULT_CODES.get(exc.status_code, "error")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error_json(exc.status_code, code, message, headers=getattr(exc, "headers", None))


async def _validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Note: we deliberately do NOT echo back the submitted values ("input"),
    # because they could include a password.
    details = [
        {
            "field": ".".join(str(part) for part in err.get("loc", ())),
            "message": err.get("msg", "Invalid value."),
            "type": err.get("type", "value_error"),
        }
        for err in exc.errors()
    ]
    return _error_json(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "validation_error",
        "Some fields are missing or invalid.",
        details,
    )


async def _unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Full details go to the server log only; the user gets a generic message.
    logger.exception("Unexpected error", exc_info=exc)
    return _error_json(500, "internal_error", "Something went wrong. Please try again.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)
