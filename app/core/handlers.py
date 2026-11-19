"""Exception handlers that give every error the same JSON envelope."""

from __future__ import annotations

import logging
import sqlite3

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, error_body

logger = logging.getLogger("app.errors")

_HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "AUTHENTICATION_FAILED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    429: "RATE_LIMITED",
}


def _json(status: int, body: dict, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content=body, headers=headers)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    headers: dict[str, str] = {}
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if exc.status_code == 429 and isinstance(exc.details, dict):
        headers["Retry-After"] = str(exc.details.get("retry_after_seconds", 60))
    return _json(exc.status_code, error_body(exc.code, exc.message, exc.details), headers)


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Never echo submitted values back (they may contain passwords).
    details = [
        {
            "field": ".".join(str(part) for part in err.get("loc", ())[1:]) or "body",
            "message": err.get("msg", "Invalid value"),
        }
        for err in exc.errors()
    ]
    return _json(422, error_body("VALIDATION_ERROR", "The request contains invalid data.", details))


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _json(exc.status_code, error_body(code, message), getattr(exc, "headers", None))


async def sqlite_error_handler(_: Request, exc: sqlite3.OperationalError) -> JSONResponse:
    if "locked" in str(exc).lower() or "busy" in str(exc).lower():
        logger.warning("database busy: %s", exc)
        return _json(503, error_body("SERVICE_BUSY", "The service is busy. Please retry."))
    logger.exception("database error")
    return _json(500, error_body("INTERNAL_ERROR", "An unexpected error occurred."))


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error: %s", type(exc).__name__)
    return _json(500, error_body("INTERNAL_ERROR", "An unexpected error occurred."))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(sqlite3.OperationalError, sqlite_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
