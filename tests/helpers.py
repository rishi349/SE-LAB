from __future__ import annotations

import sqlite3
import uuid

PASSWORD = "correct-horse-battery"
R = 100  # paise per rupee: 500 * R == ₹500


def new_key() -> str:
    return "key-" + uuid.uuid4().hex


def balance(conn: sqlite3.Connection, user_id: str) -> int:
    return conn.execute(
        "SELECT balance_paise FROM wallets WHERE user_id = ?", (user_id,)
    ).fetchone()["balance_paise"]


def ledger_entries(conn: sqlite3.Connection, transaction_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM ledger_entries WHERE transaction_id = ? ORDER BY entry_id",
        (transaction_id,),
    ).fetchall()


def count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]  # noqa: S608


def snapshot(conn: sqlite3.Connection) -> dict:
    """Full copy of all financial tables, to prove an operation changed nothing."""
    return {
        table: [tuple(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY 1")]  # noqa: S608
        for table in ("wallets", "transactions", "ledger_entries", "users")
    }
