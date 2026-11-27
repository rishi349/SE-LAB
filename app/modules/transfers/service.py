"""Ordinary user-to-user transfers.

Flow (all inside one ``BEGIN IMMEDIATE`` transaction):

1. Idempotency: if this sender already used this key, return the stored result unchanged.
2. Validate recipient, self-transfer, amount, ₹50,000 single limit, ₹1,00,000 IST-day
   limit (successful outgoing transfers only) and available balance.
3. Write the transaction row with its final status.
   * FAILED  -> no ledger entries, no balance change. Reason kept internally only.
   * SUCCESS -> one DEBIT (sender) + one CREDIT (recipient) ledger entry.

If anything raises, the whole block rolls back: no partial transfer can exist.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app.core.clock import ist_day_window, to_db, utc_now
from app.core.errors import NotFound
from app.core.ids import new_transaction_id
from app.core.money import MAX_DAILY_OUTGOING_PAISE, MAX_SINGLE_TRANSFER_PAISE, is_paise
from app.core.validators import normalize_user_id
from app.db.connection import write_transaction
from app.modules.ledger import service as ledger
from app.modules.notifications.service import notify_transaction
from app.modules.transactions.service import load_transaction_view
from app.modules.users.repository import get_active_ordinary_user, get_user, get_wallet_for_user


class FailureCode:
    """Internal failure reasons. Stored in transactions.failure_code, never returned."""

    RECIPIENT_NOT_FOUND = "RECIPIENT_NOT_FOUND"
    SELF_TRANSFER = "SELF_TRANSFER"
    INVALID_AMOUNT = "INVALID_AMOUNT"
    SINGLE_LIMIT_EXCEEDED = "SINGLE_LIMIT_EXCEEDED"
    DAILY_LIMIT_EXCEEDED = "DAILY_LIMIT_EXCEEDED"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"


@dataclass(frozen=True)
class TransferOutcome:
    transaction: dict
    replayed: bool

    @property
    def succeeded(self) -> bool:
        return self.transaction["status"] == "SUCCESS"


def successful_outgoing_today(conn: sqlite3.Connection, user_id: str, now: datetime) -> int:
    start, end = ist_day_window(now)
    row = conn.execute(
        """SELECT COALESCE(SUM(amount_paise), 0) AS total FROM transactions
           WHERE sender_user_id = ? AND type = 'TRANSFER' AND status = 'SUCCESS'
             AND created_at >= ? AND created_at < ?""",
        (user_id, to_db(start), to_db(end)),
    ).fetchone()
    return row["total"]


def _failure_reason(
    conn: sqlite3.Connection,
    sender_id: str,
    recipient: sqlite3.Row | None,
    amount_paise: int,
    now: datetime,
) -> str | None:
    if recipient is None:
        return FailureCode.RECIPIENT_NOT_FOUND
    if recipient["user_id"] == sender_id:
        return FailureCode.SELF_TRANSFER
    if amount_paise <= 0:
        return FailureCode.INVALID_AMOUNT
    if amount_paise > MAX_SINGLE_TRANSFER_PAISE:
        return FailureCode.SINGLE_LIMIT_EXCEEDED
    if successful_outgoing_today(conn, sender_id, now) + amount_paise > MAX_DAILY_OUTGOING_PAISE:
        return FailureCode.DAILY_LIMIT_EXCEEDED
    if get_wallet_for_user(conn, sender_id)["balance_paise"] < amount_paise:
        return FailureCode.INSUFFICIENT_BALANCE
    return None


def execute_transfer(
    conn: sqlite3.Connection,
    *,
    sender_user_id: str,
    recipient_user_id: str,
    amount_paise: int,
    idempotency_key: str,
    now: datetime | None = None,
) -> TransferOutcome:
    if not is_paise(amount_paise):
        raise TypeError("amount_paise must be an int")
    now = now or utc_now()
    ts = to_db(now)
    recipient_ref = normalize_user_id(recipient_user_id)

    with write_transaction(conn):
        existing = ledger.find_by_idempotency_key(conn, sender_user_id, idempotency_key)
        if existing is not None:
            view = load_transaction_view(conn, existing["transaction_id"], sender_user_id)
            return TransferOutcome(transaction=view, replayed=True)

        sender = get_user(conn, sender_user_id)
        if sender is None or sender["status"] != "ACTIVE" or sender["role"] != "user":
            raise NotFound("Sender account is not active.", code="SENDER_NOT_ACTIVE")

        recipient = get_active_ordinary_user(conn, recipient_ref)
        failure = _failure_reason(conn, sender_user_id, recipient, amount_paise, now)
        transaction_id = new_transaction_id()

        ledger.insert_transaction(
            conn,
            transaction_id=transaction_id,
            type_="TRANSFER",
            status="FAILED" if failure else "SUCCESS",
            sender_user_id=sender_user_id,
            recipient_user_id=recipient["user_id"] if recipient else None,
            recipient_ref=recipient_ref,
            amount_paise=amount_paise,
            failure_code=failure,
            idempotency_key=idempotency_key,
            created_at=ts,
        )
        if failure is None:
            sender_wallet = get_wallet_for_user(conn, sender_user_id)["wallet_id"]
            recipient_wallet = get_wallet_for_user(conn, recipient["user_id"])["wallet_id"]
            ledger.debit(conn, transaction_id, sender_wallet, amount_paise, ts)
            ledger.credit(conn, transaction_id, recipient_wallet, amount_paise, ts)

        view = load_transaction_view(conn, transaction_id, sender_user_id)
    # After COMMIT, best-effort: never changes the outcome above.
    notify_transaction(conn, transaction_id, now)
    return TransferOutcome(transaction=view, replayed=False)
