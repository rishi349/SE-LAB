from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, get_current_user, get_db
from app.core.schemas import ERROR_RESPONSES
from app.modules.wallets import service
from app.modules.wallets.schemas import WalletOut

router = APIRouter(prefix="/wallets", tags=["Wallets"], responses=ERROR_RESPONSES)


@router.get("/me", response_model=WalletOut, summary="View my wallet and balance")
def get_my_wallet(
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.get_my_wallet(conn, user.user_id)
