"""Admin-only operations: search users by User ID and fund user wallets.

Admin funding is NOT a transfer: it is not subject to transfer limits, does not need or
debit the admin's own wallet, and is recorded as an ADMIN_FUNDING transaction with a
single CREDIT ledger entry on the recipient's wallet. There is no system funding account,
no initial allocation and no cap.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from app.core.clock import to_db, utc_now
from app.core.errors import NotFound, PermissionDenied, ValidationFailed
from app.core.ids import new_transaction_id
from app.core.money import is_paise
from app.core.validators import normalize_user_id
from app.db.connection import write_transaction
from app.modules.ledger import service as ledger
from app.modules.notifications.service import notify_transaction
from app.modules.transactions.service import load_transaction_view
from app.modules.users.repository import get_active_ordinary_user, get_user, get_wallet_for_user


def search_user_by_id(conn: sqlite3.Connection, user_id: str) -> dict:
    """Exact User ID match only. Returns basic info: User ID and name."""
    row = get_active_ordinary_user(conn, normalize_user_id(user_id))
    if row is None:
        raise NotFound("No active user with this User ID.", code="USER_NOT_FOUND")
    return {"user_id": row["user_id"], "name": row["name"]}


def fund_wallet(
    conn: sqlite3.Connection,
    *,
    admin_user_id: str,
    recipient_user_id: str,
    amount_paise: int,
    idempotency_key: str,
    now: datetime | None = None,
) -> tuple[dict, bool]:
    """Credit a user's wallet. Returns (transaction view, replayed)."""
    if not is_paise(amount_paise):
        raise TypeError("amount_paise must be an int")
    now = now or utc_now()
    ts = to_db(now)
    recipient_id = normalize_user_id(recipient_user_id)

    with write_transaction(conn):
        existing = ledger.find_by_idempotency_key(conn, admin_user_id, idempotency_key)
        if existing is not None:
            return load_transaction_view(conn, existing["transaction_id"], admin_user_id), True

        admin = get_user(conn, admin_user_id)
        if admin is None or admin["role"] != "admin" or admin["status"] != "ACTIVE":
            raise PermissionDenied("Administrator privileges are required.")
        if amount_paise <= 0:
            raise ValidationFailed(
                "Amount must be a positive number of paise.", code="INVALID_AMOUNT"
            )
        recipient = get_active_ordinary_user(conn, recipient_id)
        if recipient is None:
            raise NotFound("No active user with this User ID.", code="USER_NOT_FOUND")
        wallet_id = get_wallet_for_user(conn, recipient_id)["wallet_id"]
        if not ledger.can_credit(conn, wallet_id, amount_paise):
            raise ValidationFailed("Amount is too large to store.", code="AMOUNT_OUT_OF_RANGE")

        transaction_id = new_transaction_id()
        ledger.insert_transaction(
            conn,
            transaction_id=transaction_id,
            type_="ADMIN_FUNDING",
            status="SUCCESS",
            sender_user_id=admin_user_id,
            recipient_user_id=recipient_id,
            recipient_ref=recipient_id,
            amount_paise=amount_paise,
            failure_code=None,
            idempotency_key=idempotency_key,
            created_at=ts,
        )
        ledger.credit(conn, transaction_id, wallet_id, amount_paise, ts)
        view = load_transaction_view(conn, transaction_id, admin_user_id)
    # After COMMIT, best-effort: never changes the outcome above.
    notify_transaction(conn, transaction_id, now)
    return view, False
