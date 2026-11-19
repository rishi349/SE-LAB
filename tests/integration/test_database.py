"""Database-level guarantees: constraints, foreign keys and immutability triggers."""

import sqlite3

import pytest

from tests.helpers import R, new_key


def test_foreign_keys_are_enforced(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO wallets (wallet_id, user_id, balance_paise, created_at, updated_at)"
            " VALUES ('WALX', 'USR-DOES-NOT-EXIST', 0, 't', 't')"
        )


def test_wallet_balance_cannot_go_negative_or_be_a_float(conn, make_user):
    user = make_user()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE wallets SET balance_paise = -1 WHERE user_id = ?", (user["user_id"],))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE wallets SET balance_paise = 1.5 WHERE user_id = ?", (user["user_id"],))


def test_ledger_and_transactions_are_immutable(conn, make_user, fund):
    user = make_user()
    txn = fund(user["user_id"], 100 * R)
    for sql in (
        "UPDATE ledger_entries SET amount_paise = 1",
        "DELETE FROM ledger_entries",
        "UPDATE transactions SET amount_paise = 1",
        "DELETE FROM transactions",
    ):
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(sql)
    assert (
        conn.execute(
            "SELECT amount_paise FROM transactions WHERE transaction_id = ?",
            (txn["transaction_id"],),
        ).fetchone()[0]
        == 100 * R
    )


def test_wallets_and_users_cannot_be_deleted(conn, make_user):
    user = make_user()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM wallets WHERE user_id = ?", (user["user_id"],))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM users WHERE user_id = ?", (user["user_id"],))


@pytest.mark.parametrize(
    ("column", "value"),
    [("user_id", "USRCHANGED000"), ("role", "admin"), ("email", "new@example.com")],
)
def test_permanent_user_fields_cannot_change(conn, make_user, column, value):
    user = make_user()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            f"UPDATE users SET {column} = ? WHERE user_id = ?",  # noqa: S608
            (value, user["user_id"]),
        )


def test_successful_transaction_requires_positive_amount(conn, make_user):
    a, b = make_user(), make_user()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO transactions (transaction_id, type, status, sender_user_id,
                 recipient_user_id, recipient_ref, amount_paise, failure_code, idempotency_key,
                 created_at) VALUES ('TXNX', 'TRANSFER', 'SUCCESS', ?, ?, ?, 0, NULL, ?, 't')""",
            (a["user_id"], b["user_id"], b["user_id"], new_key()),
        )


def test_idempotency_key_unique_per_sender(conn, make_user):
    a, b = make_user(), make_user()
    sql = """INSERT INTO transactions (transaction_id, type, status, sender_user_id,
               recipient_user_id, recipient_ref, amount_paise, failure_code, idempotency_key,
               created_at) VALUES (?, 'TRANSFER', 'FAILED', ?, ?, ?, 1, 'X', 'same-key', 't')"""
    conn.execute(sql, ("TXN1", a["user_id"], b["user_id"], b["user_id"]))
    conn.execute(sql, ("TXN2", b["user_id"], a["user_id"], a["user_id"]))  # other sender: fine
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql, ("TXN3", a["user_id"], b["user_id"], b["user_id"]))
