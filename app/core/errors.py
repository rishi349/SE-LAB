"""Application errors. Services raise these; the API layer turns them into JSON.

Every error response has the same shape::

    {"error": {"code": "SOME_CODE", "message": "Human readable.", "details": null}}
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"
    message = "The request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        super().__init__(self.message)


class ValidationFailed(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "The request contains invalid data."


class AuthenticationFailed(AppError):
    status_code = 401
    code = "AUTHENTICATION_FAILED"
    message = "Authentication is required or the credentials are invalid."


class PermissionDenied(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "The requested resource was not found."


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "The request conflicts with the current state."


class RateLimited(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "Too many requests. Please try again later."


class ServiceBusy(AppError):
    status_code = 503
    code = "SERVICE_BUSY"
    message = "The service is busy. Please retry the request."


def error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}
