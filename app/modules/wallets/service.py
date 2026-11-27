"""Wallet viewing. Wallets are created only at registration and are never deleted."""

from __future__ import annotations

import sqlite3

from app.core.errors import NotFound
from app.core.money import format_rupees
from app.modules.users.repository import get_wallet_for_user


def wallet_view(row: sqlite3.Row) -> dict:
    return {
        "wallet_id": row["wallet_id"],
        "user_id": row["user_id"],
        "balance_paise": row["balance_paise"],
        "balance": format_rupees(row["balance_paise"]),
        "currency": "INR",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_my_wallet(conn: sqlite3.Connection, user_id: str) -> dict:
    row = get_wallet_for_user(conn, user_id)
    if row is None:
        raise NotFound("Wallet not found.", code="WALLET_NOT_FOUND")
    return wallet_view(row)
