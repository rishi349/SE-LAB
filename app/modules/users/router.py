from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Path, status

from app.core.deps import (
    CurrentUser,
    get_current_user,
    get_db,
    rate_limit_by_user,
    require_ordinary_user,
)
from app.core.ids import USER_ID_PATTERN
from app.core.schemas import ERROR_RESPONSES, ErrorResponse
from app.modules.users import service
from app.modules.users.schemas import (
    AccountDeletionRequest,
    AccountDeletionResponse,
    ProfileOut,
    UpdateProfileRequest,
    UserLookupOut,
)

router = APIRouter(prefix="/users", tags=["Users"], responses=ERROR_RESPONSES)


@router.get("/me", response_model=ProfileOut, summary="View my profile")
def get_my_profile(
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.get_profile(conn, user.user_id)


@router.patch(
    "/me",
    response_model=ProfileOut,
    responses={409: {"model": ErrorResponse, "description": "Name-change cooldown active"}},
    dependencies=[Depends(rate_limit_by_user("profile_update"))],
    summary="Change my name (once every 60 days)",
)
def update_my_profile(
    body: UpdateProfileRequest,
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.change_name(conn, user.user_id, body.name)


@router.post(
    "/me/deletion-request",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AccountDeletionResponse,
    responses={409: {"model": ErrorResponse, "description": "Wallet balance not settled"}},
    dependencies=[Depends(rate_limit_by_user("account_deletion"))],
    summary="Deactivate my account; personal data is deleted after 7 days",
)
def request_deletion(
    body: AccountDeletionRequest,
    user: CurrentUser = Depends(require_ordinary_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.request_account_deletion(conn, user.user_id, body.password)


@router.get(
    "/{user_id}",
    response_model=UserLookupOut,
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(rate_limit_by_user("lookup"))],
    summary="Look up a recipient by User ID (returns User ID and name only)",
)
def lookup_user(
    user_id: str = Path(pattern=USER_ID_PATTERN),
    _: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.lookup_recipient(conn, user_id)
