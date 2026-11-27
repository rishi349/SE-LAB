"""FastAPI dependencies: DB connection, settings, current user, roles and rate limits."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.core.errors import AuthenticationFailed, PermissionDenied, RateLimited
from app.core.rate_limit import RATE_LIMITS, SlidingWindowRateLimiter
from app.core.security import decode_access_token
from app.db.connection import connect
from app.modules.users.repository import get_user

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token from /auth/login")


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    role: str
    name: str
    email: str


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.settings.database_path)
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationFailed()
    claims = decode_access_token(credentials.credentials, settings.jwt_secret)
    row = get_user(conn, claims["sub"])
    # Role and status always come from the database, never from the token alone.
    if row is None or row["status"] != "ACTIVE":
        raise AuthenticationFailed()
    return CurrentUser(
        user_id=row["user_id"], role=row["role"], name=row["name"], email=row["email"]
    )


def require_ordinary_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "user":
        raise PermissionDenied("This action is available to ordinary users only.")
    return user


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "admin":
        raise PermissionDenied("Administrator privileges are required.")
    return user


def _limiter(request: Request) -> SlidingWindowRateLimiter:
    return request.app.state.rate_limiter


def _enforce(request: Request, scope: str, subject: str) -> None:
    if not request.app.state.settings.rate_limit_enabled:
        return
    limit, window = RATE_LIMITS[scope]
    retry_after = _limiter(request).hit(f"{scope}:{subject}", limit, window)
    if retry_after is not None:
        raise RateLimited(details={"retry_after_seconds": retry_after})


def rate_limit_by_ip(scope: str) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        _enforce(request, scope, client)

    return dependency


def rate_limit_by_user(scope: str) -> Callable[..., None]:
    def dependency(request: Request, user: CurrentUser = Depends(get_current_user)) -> None:
        _enforce(request, scope, user.user_id)

    return dependency
