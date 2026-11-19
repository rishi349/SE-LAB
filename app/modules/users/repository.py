"""Read helpers for users and wallets, shared by several modules."""

from __future__ import annotations

import sqlite3


def get_user(conn: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def get_user_by_email(conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_active_ordinary_user(conn: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
    """A user who can receive transfers/funding: exists, role 'user', status ACTIVE."""
    return conn.execute(
        "SELECT * FROM users WHERE user_id = ? AND role = 'user' AND status = 'ACTIVE'",
        (user_id,),
    ).fetchone()


def get_wallet_for_user(conn: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM wallets WHERE user_id = ?", (user_id,)).fetchone()
