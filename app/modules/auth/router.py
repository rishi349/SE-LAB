from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, status

from app.config import Settings
from app.core.deps import get_db, get_settings, rate_limit_by_ip
from app.core.schemas import ErrorResponse
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    dependencies=[Depends(rate_limit_by_ip("register"))],
    summary="Register a new user (wallet is created automatically with ₹0)",
)
def register(
    body: RegisterRequest,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return service.register_user(
        conn,
        name=body.name,
        email=body.email,
        password=body.password,
        bcrypt_rounds=settings.bcrypt_rounds,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
    dependencies=[Depends(rate_limit_by_ip("login"))],
    summary="Log in with email and password and receive a 1-hour JWT",
)
def login(
    body: LoginRequest,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return service.login(
        conn,
        email=body.email,
        password=body.password,
        jwt_secret=settings.jwt_secret,
        bcrypt_rounds=settings.bcrypt_rounds,
    )
