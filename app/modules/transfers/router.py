from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.responses import JSONResponse

from app.core.deps import CurrentUser, get_db, rate_limit_by_user, require_ordinary_user
from app.core.errors import error_body
from app.core.idempotency import IDEMPOTENCY_HEADER, REPLAY_HEADER, require_idempotency_key
from app.core.schemas import ERROR_RESPONSES, ErrorResponse, TransactionOut
from app.modules.transfers import service
from app.modules.transfers.schemas import TransferRequest

router = APIRouter(tags=["Transfers"], responses=ERROR_RESPONSES)

TRANSFER_FAILED_MESSAGE = "The transfer could not be completed."


@router.post(
    "/transfers",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionOut,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Validation error, or TRANSFER_FAILED (attempt recorded, no money "
            "moved; error.details.transaction holds the failed record).",
        }
    },
    dependencies=[Depends(rate_limit_by_user("transfer"))],
    summary="Send money to another user (requires an Idempotency-Key header)",
)
def create_transfer(
    body: TransferRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_HEADER),
    user: CurrentUser = Depends(require_ordinary_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    key = require_idempotency_key(idempotency_key)
    outcome = service.execute_transfer(
        conn,
        sender_user_id=user.user_id,
        recipient_user_id=body.recipient_user_id,
        amount_paise=body.amount_paise,
        idempotency_key=key,
    )
    headers = {REPLAY_HEADER: "true"} if outcome.replayed else {}
    if not outcome.succeeded:
        # Same body for every failure reason: the internal reason is never revealed.
        return JSONResponse(
            status_code=422,
            content=error_body(
                "TRANSFER_FAILED",
                TRANSFER_FAILED_MESSAGE,
                details={"transaction": outcome.transaction},
            ),
            headers=headers,
        )
    response.headers.update(headers)
    return outcome.transaction
