"""Low-level money movement. Callers MUST already be inside ``write_transaction``.

These functions are the only code that changes ``wallets.balance_paise``. Every change
writes exactly one immutable ledger entry carrying the resulting balance.
"""

from __future__ import annotations

import sqlite3

from app.core.money import SQLITE_MAX_INTEGER


class LedgerInvariantError(RuntimeError):
    """Raised when a balance update unexpectedly fails; the whole transaction rolls back."""


def find_by_idempotency_key(
    conn: sqlite3.Connection, sender_user_id: str, idempotency_key: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT transaction_id FROM transactions WHERE sender_user_id = ? AND idempotency_key = ?",
        (sender_user_id, idempotency_key),
    ).fetchone()


def insert_transaction(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    type_: str,
    status: str,
    sender_user_id: str,
    recipient_user_id: str | None,
    recipient_ref: str,
    amount_paise: int,
    failure_code: str | None,
    idempotency_key: str,
    created_at: str,
) -> None:
    conn.execute(
        """INSERT INTO transactions (transaction_id, type, status, sender_user_id,
               recipient_user_id, recipient_ref, amount_paise, failure_code,
               idempotency_key, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            transaction_id,
            type_,
            status,
            sender_user_id,
            recipient_user_id,
            recipient_ref,
            amount_paise,
            failure_code,
            idempotency_key,
            created_at,
        ),
    )


def _balance(conn: sqlite3.Connection, wallet_id: str) -> int:
    return conn.execute(
        "SELECT balance_paise FROM wallets WHERE wallet_id = ?", (wallet_id,)
    ).fetchone()["balance_paise"]


def _write_entry(
    conn: sqlite3.Connection,
    transaction_id: str,
    wallet_id: str,
    entry_type: str,
    amount_paise: int,
    created_at: str,
) -> int:
    balance_after = _balance(conn, wallet_id)
    conn.execute(
        """INSERT INTO ledger_entries (transaction_id, wallet_id, entry_type, amount_paise,
               balance_after_paise, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (transaction_id, wallet_id, entry_type, amount_paise, balance_after, created_at),
    )
    return balance_after


def debit(
    conn: sqlite3.Connection, transaction_id: str, wallet_id: str, amount_paise: int, ts: str
) -> int:
    # The WHERE clause is a second guard on top of the balance check done by the caller
    # (and the CHECK balance_paise >= 0 constraint is a third).
    cursor = conn.execute(
        """UPDATE wallets SET balance_paise = balance_paise - ?, updated_at = ?
           WHERE wallet_id = ? AND balance_paise >= ?""",
        (amount_paise, ts, wallet_id, amount_paise),
    )
    if cursor.rowcount != 1:
        raise LedgerInvariantError("debit would make the balance negative")
    return _write_entry(conn, transaction_id, wallet_id, "DEBIT", amount_paise, ts)


def credit(
    conn: sqlite3.Connection, transaction_id: str, wallet_id: str, amount_paise: int, ts: str
) -> int:
    cursor = conn.execute(
        """UPDATE wallets SET balance_paise = balance_paise + ?, updated_at = ?
           WHERE wallet_id = ? AND balance_paise <= ?""",
        (amount_paise, ts, wallet_id, SQLITE_MAX_INTEGER - amount_paise),
    )
    if cursor.rowcount != 1:
        raise LedgerInvariantError("credit would overflow the balance")
    return _write_entry(conn, transaction_id, wallet_id, "CREDIT", amount_paise, ts)


def can_credit(conn: sqlite3.Connection, wallet_id: str, amount_paise: int) -> bool:
    return _balance(conn, wallet_id) <= SQLITE_MAX_INTEGER - amount_paise
