"""Registration (user + wallet in one DB transaction), admin creation and login."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from app.core.clock import to_db, utc_now
from app.core.errors import AuthenticationFailed, Conflict
from app.core.ids import new_user_id, new_wallet_id
from app.core.security import (
    ACCESS_TOKEN_TTL,
    burn_password_check,
    create_access_token,
    hash_password,
    verify_password,
)
from app.core.validators import check_new_password, normalize_email, normalize_name
from app.db.connection import write_transaction
from app.modules.users.repository import get_user, get_user_by_email, get_wallet_for_user
from app.modules.users.service import profile_view
from app.modules.wallets.service import wallet_view


def _create_account(
    conn: sqlite3.Connection,
    *,
    role: str,
    name: str,
    email: str,
    password: str,
    bcrypt_rounds: int,
    now: datetime | None,
) -> dict:
    name = normalize_name(name)
    email = normalize_email(email)
    check_new_password(password)
    password_hash = hash_password(password, bcrypt_rounds)  # slow: done before taking the lock
    ts = to_db(now or utc_now())

    with write_transaction(conn):
        if get_user_by_email(conn, email) is not None:
            raise Conflict(
                "An account with this email already exists.", code="EMAIL_ALREADY_REGISTERED"
            )
        user_id = new_user_id()
        conn.execute(
            """INSERT INTO users (user_id, email, name, password_hash, role, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)""",
            (user_id, email, name, password_hash, role, ts),
        )
        # The wallet is created in the same transaction: no user ever exists without one.
        conn.execute(
            """INSERT INTO wallets (wallet_id, user_id, balance_paise, created_at, updated_at)
               VALUES (?, ?, 0, ?, ?)""",
            (new_wallet_id(), user_id, ts, ts),
        )

    return {
        "user": profile_view(get_user(conn, user_id)),
        "wallet": wallet_view(get_wallet_for_user(conn, user_id)),
    }


def register_user(
    conn: sqlite3.Connection,
    *,
    name: str,
    email: str,
    password: str,
    bcrypt_rounds: int,
    now: datetime | None = None,
) -> dict:
    """Public registration. Always creates role 'user'."""
    return _create_account(
        conn,
        role="user",
        name=name,
        email=email,
        password=password,
        bcrypt_rounds=bcrypt_rounds,
        now=now,
    )


def create_admin(
    conn: sqlite3.Connection,
    *,
    name: str,
    email: str,
    password: str,
    bcrypt_rounds: int,
    now: datetime | None = None,
) -> dict:
    """Explicit admin creation. Only reachable from scripts/create_admin.py, never the API."""
    return _create_account(
        conn,
        role="admin",
        name=name,
        email=email,
        password=password,
        bcrypt_rounds=bcrypt_rounds,
        now=now,
    )


def login(
    conn: sqlite3.Connection,
    *,
    email: str,
    password: str,
    jwt_secret: str,
    bcrypt_rounds: int,
) -> dict:
    try:
        email = normalize_email(email)
    except ValueError:
        email = ""
    row = get_user_by_email(conn, email) if email else None
    if row is None:
        burn_password_check(password, bcrypt_rounds)
        raise AuthenticationFailed("Invalid email or password.", code="INVALID_CREDENTIALS")
    password_ok = verify_password(password, row["password_hash"])
    # Deactivated users get the same message as a wrong password.
    if not password_ok or row["status"] != "ACTIVE":
        raise AuthenticationFailed("Invalid email or password.", code="INVALID_CREDENTIALS")
    token = create_access_token(row["user_id"], row["role"], jwt_secret)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
    }
