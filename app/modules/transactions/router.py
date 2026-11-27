from __future__ import annotations

import sqlite3
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel

from app.core.deps import CurrentUser, get_current_user, get_db
from app.core.ids import TRANSACTION_ID_PATTERN
from app.core.schemas import ERROR_RESPONSES, ErrorResponse, Pagination, TransactionOut
from app.modules.transactions import service

router = APIRouter(prefix="/transactions", tags=["Transaction history"], responses=ERROR_RESPONSES)


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    pagination: Pagination


@router.get(
    "",
    response_model=TransactionPage,
    summary="My transaction history (newest first, paginated, filterable)",
)
def list_my_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(service.DEFAULT_PAGE_SIZE, ge=1, le=service.MAX_PAGE_SIZE),
    status: Literal["SUCCESS", "FAILED"] | None = Query(None),
    direction: Literal["INCOMING", "OUTGOING"] | None = Query(None),
    from_date: date | None = Query(None, description="Inclusive, IST calendar date"),
    to_date: date | None = Query(None, description="Inclusive, IST calendar date"),
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.list_history(
        conn,
        user.user_id,
        page=page,
        page_size=page_size,
        status=status,
        direction=direction,
        from_date=from_date,
        to_date=to_date,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionOut,
    responses={404: {"model": ErrorResponse}},
    summary="One of my transactions",
)
def get_my_transaction(
    transaction_id: str = Path(pattern=TRANSACTION_ID_PATTERN),
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.get_transaction_for_user(conn, user.user_id, transaction_id)
