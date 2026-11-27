from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Header, Path, Response, status

from app.core.deps import CurrentUser, get_db, rate_limit_by_user, require_admin
from app.core.idempotency import IDEMPOTENCY_HEADER, REPLAY_HEADER, require_idempotency_key
from app.core.ids import USER_ID_PATTERN
from app.core.schemas import ERROR_RESPONSES, ErrorResponse, TransactionOut
from app.modules.admin import service
from app.modules.admin.schemas import AdminUserOut, FundingRequest

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    responses=ERROR_RESPONSES,
    dependencies=[Depends(require_admin)],
)


@router.get(
    "/users/{user_id}",
    response_model=AdminUserOut,
    responses={404: {"model": ErrorResponse}},
    summary="Find a user by exact User ID (no email search)",
)
def get_user_by_id(
    user_id: str = Path(pattern=USER_ID_PATTERN),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.search_user_by_id(conn, user_id)


@router.post(
    "/fundings",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionOut,
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(rate_limit_by_user("admin_funding"))],
    summary="Fund a user's wallet (requires an Idempotency-Key header)",
)
def fund_user_wallet(
    body: FundingRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_HEADER),
    admin: CurrentUser = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    key = require_idempotency_key(idempotency_key)
    view, replayed = service.fund_wallet(
        conn,
        admin_user_id=admin.user_id,
        recipient_user_id=body.recipient_user_id,
        amount_paise=body.amount_paise,
        idempotency_key=key,
    )
    if replayed:
        response.headers[REPLAY_HEADER] = "true"
    return view
