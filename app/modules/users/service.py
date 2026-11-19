"""Profile management, recipient lookup and account deletion."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from app.core.clock import from_db, to_db, utc_now
from app.core.errors import AuthenticationFailed, Conflict, NotFound, PermissionDenied
from app.core.security import verify_password
from app.core.validators import normalize_name, normalize_user_id
from app.db.connection import write_transaction
from app.modules.users.repository import get_active_ordinary_user, get_user, get_wallet_for_user

NAME_CHANGE_COOLDOWN = timedelta(days=60)
DELETION_WAITING_PERIOD = timedelta(days=7)


def profile_view(row: sqlite3.Row) -> dict:
    changed = row["name_changed_at"]
    next_allowed = to_db(from_db(changed) + NAME_CHANGE_COOLDOWN) if changed else None
    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"],
        "name_changed_at": changed,
        "next_name_change_allowed_at": next_allowed,
    }


def get_profile(conn: sqlite3.Connection, user_id: str) -> dict:
    row = get_user(conn, user_id)
    if row is None:
        raise NotFound()
    return profile_view(row)


def change_name(
    conn: sqlite3.Connection, user_id: str, new_name: str, now: datetime | None = None
) -> dict:
    """Name may change once every 60 days, counted from the last successful change."""
    now = now or utc_now()
    new_name = normalize_name(new_name)
    with write_transaction(conn):
        row = get_user(conn, user_id)
        if row is None or row["status"] != "ACTIVE":
            raise NotFound()
        if row["name"] == new_name:
            # Nothing changes, so the cooldown is not started or consumed.
            return profile_view(row)
        if row["name_changed_at"]:
            next_allowed = from_db(row["name_changed_at"]) + NAME_CHANGE_COOLDOWN
            if now < next_allowed:
                raise Conflict(
                    "Your name can be changed only once every 60 days.",
                    code="NAME_CHANGE_COOLDOWN",
                    details={"next_name_change_allowed_at": to_db(next_allowed)},
                )
        conn.execute(
            "UPDATE users SET name = ?, name_changed_at = ? WHERE user_id = ?",
            (new_name, to_db(now), user_id),
        )
    return get_profile(conn, user_id)


def lookup_recipient(conn: sqlite3.Connection, user_id: str) -> dict:
    """Confirm a recipient before sending: returns only User ID and name."""
    row = get_active_ordinary_user(conn, normalize_user_id(user_id))
    if row is None:
        raise NotFound("No active user with this User ID.", code="USER_NOT_FOUND")
    return {"user_id": row["user_id"], "name": row["name"]}


def request_account_deletion(
    conn: sqlite3.Connection, user_id: str, password: str, now: datetime | None = None
) -> dict:
    """Deactivate now; personal data is deleted after the 7-day waiting period.

    The wallet balance must be exactly ₹0 (settled) first. Financial records are kept.
    """
    now = now or utc_now()
    row = get_user(conn, user_id)
    if row is None or row["status"] != "ACTIVE":
        raise NotFound()
    if row["role"] != "user":
        raise PermissionDenied("Administrator accounts cannot be deleted through the API.")
    if not verify_password(password, row["password_hash"]):
        raise AuthenticationFailed("Password is incorrect.", code="INVALID_CREDENTIALS")

    due = now + DELETION_WAITING_PERIOD
    with write_transaction(conn):
        # Re-check inside the write lock so an incoming transfer cannot slip in between.
        row = get_user(conn, user_id)
        if row is None or row["status"] != "ACTIVE":
            raise NotFound()
        wallet = get_wallet_for_user(conn, user_id)
        if wallet["balance_paise"] != 0:
            raise Conflict(
                "Your wallet balance must be ₹0 before the account can be deleted.",
                code="BALANCE_NOT_SETTLED",
                details={"balance_paise": wallet["balance_paise"]},
            )
        conn.execute(
            """UPDATE users SET status = 'DEACTIVATED', deactivated_at = ?, deletion_due_at = ?
               WHERE user_id = ?""",
            (to_db(now), to_db(due), user_id),
        )
    return {
        "user_id": user_id,
        "status": "DEACTIVATED",
        "deactivated_at": to_db(now),
        "personal_data_deletion_due_at": to_db(due),
    }


def purge_expired_accounts(conn: sqlite3.Connection, now: datetime | None = None) -> int:
    """Erase personal data of accounts whose 7-day waiting period has ended.

    Name, email and password hash are removed. The User ID, wallet row, transactions and
    ledger entries are retained because they are financial records.
    """
    now = now or utc_now()
    ts = to_db(now)
    with write_transaction(conn):
        cursor = conn.execute(
            """UPDATE users
               SET name = NULL, email = NULL, password_hash = NULL,
                   status = 'DELETED', personal_data_deleted_at = ?
               WHERE status = 'DEACTIVATED' AND deletion_due_at <= ?""",
            (ts, ts),
        )
        return cursor.rowcount
