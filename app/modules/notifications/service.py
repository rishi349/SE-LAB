"""In-app notifications.

Rules (see docs/notifications-design.md):
* Notifications are written only AFTER the money transaction has committed, in their own
  short transaction. Any error is logged and swallowed, so a notification can never change
  the result of a transfer or an admin funding.
* Idempotent replays never reach the notifier, and UNIQUE(user_id, transaction_id, type) is
  a second guard against duplicates.
* No message text is stored. Messages are built on read from the counterparty's current
  name, so a deleted user's name never lingers. Failure reasons are never mentioned.
* Notifications are not financial records: no ledger entries, no balance changes.
"""

from __future__ import annotations

import logging
import math
import sqlite3
from datetime import datetime

from app.core.clock import to_db, utc_now
from app.core.errors import NotFound, ValidationFailed
from app.core.money import format_inr
from app.db.connection import write_transaction

logger = logging.getLogger("app.notifications")

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20
DELETED_USER = "a deleted user"

TRANSFER_SENT = "TRANSFER_SENT"
TRANSFER_RECEIVED = "TRANSFER_RECEIVED"
TRANSFER_FAILED = "TRANSFER_FAILED"
WALLET_FUNDED = "WALLET_FUNDED"


# ---------------------------------------------------------------- writing


def _build_rows(txn: sqlite3.Row, created_at: str) -> list[tuple]:
    """Who gets which notification for one stored transaction."""
    tid, amount = txn["transaction_id"], txn["amount_paise"]
    sender, recipient = txn["sender_user_id"], txn["recipient_user_id"]
    if txn["type"] == "ADMIN_FUNDING":
        return [(recipient, WALLET_FUNDED, tid, None, amount, created_at)]
    if txn["status"] == "SUCCESS":
        return [
            (sender, TRANSFER_SENT, tid, recipient, amount, created_at),
            (recipient, TRANSFER_RECEIVED, tid, sender, amount, created_at),
        ]
    # Failed attempt: sender only (team decision), whatever the recipient was.
    return [(sender, TRANSFER_FAILED, tid, recipient, amount, created_at)]


def notify_transaction(
    conn: sqlite3.Connection, transaction_id: str, now: datetime | None = None
) -> None:
    """Best-effort: create the notifications for a committed transaction. Never raises."""
    try:
        txn = conn.execute(
            """SELECT transaction_id, type, status, sender_user_id, recipient_user_id,
                      amount_paise FROM transactions WHERE transaction_id = ?""",
            (transaction_id,),
        ).fetchone()
        if txn is None:
            return
        rows = _build_rows(txn, to_db(now or utc_now()))
        with write_transaction(conn):
            conn.executemany(
                """INSERT OR IGNORE INTO notifications (user_id, type, transaction_id,
                       counterparty_user_id, amount_paise, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                rows,
            )
    except Exception:  # notifications must never break money movement
        # Log only the transaction ID: no names, emails or amounts.
        logger.warning("could not create notifications for %s", transaction_id, exc_info=True)


# ---------------------------------------------------------------- reading


def _message(row: sqlite3.Row) -> str:
    amount = format_inr(row["amount_paise"])
    name = row["counterparty_name"] or DELETED_USER
    kind = row["type"]
    if kind == TRANSFER_SENT:
        return f"You sent {amount} to {name}."
    if kind == TRANSFER_RECEIVED:
        return f"You received {amount} from {name}."
    if kind == WALLET_FUNDED:
        return f"{amount} was added to your wallet."
    if row["counterparty_user_id"] is not None:
        return f"Your transfer of {amount} to {name} could not be completed."
    return f"Your transfer of {amount} could not be completed."


def notification_view(row: sqlite3.Row) -> dict:
    return {
        "notification_id": row["notification_id"],
        "type": row["type"],
        "message": _message(row),
        "amount_paise": row["amount_paise"],
        "transaction_id": row["transaction_id"],
        "is_read": bool(row["is_read"]),
        "created_at": row["created_at"],
        "read_at": row["read_at"],
    }


_SELECT = """
SELECT n.notification_id, n.type, n.transaction_id, n.counterparty_user_id, n.amount_paise,
       n.is_read, n.created_at, n.read_at, u.name AS counterparty_name
FROM notifications n
LEFT JOIN users u ON u.user_id = n.counterparty_user_id
"""


def unread_count(conn: sqlite3.Connection, user_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,)
    ).fetchone()["n"]


def list_notifications(
    conn: sqlite3.Connection,
    user_id: str,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    unread_only: bool = False,
) -> dict:
    if page < 1 or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValidationFailed(f"page must be >= 1 and page_size between 1 and {MAX_PAGE_SIZE}.")
    only_unread = 1 if unread_only else 0
    total = conn.execute(
        """SELECT COUNT(*) AS n FROM notifications n
           WHERE n.user_id = ? AND (? = 0 OR n.is_read = 0)""",
        (user_id, only_unread),
    ).fetchone()["n"]
    rows = conn.execute(
        _SELECT
        + """ WHERE n.user_id = ? AND (? = 0 OR n.is_read = 0)
              ORDER BY n.created_at DESC, n.notification_id DESC LIMIT ? OFFSET ?""",
        (user_id, only_unread, page_size, (page - 1) * page_size),
    ).fetchall()
    return {
        "items": [notification_view(r) for r in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": math.ceil(total / page_size) if total else 0,
        },
        "unread_count": unread_count(conn, user_id),
    }


# ---------------------------------------------------------------- marking read


def mark_read(
    conn: sqlite3.Connection, user_id: str, notification_id: int, now: datetime | None = None
) -> dict:
    """Mark one of the user's notifications as read. Marking twice is harmless."""
    with write_transaction(conn):
        cursor = conn.execute(
            """UPDATE notifications SET is_read = 1, read_at = COALESCE(read_at, ?)
               WHERE notification_id = ? AND user_id = ?""",
            (to_db(now or utc_now()), notification_id, user_id),
        )
        if cursor.rowcount == 0:
            # Same answer for "doesn't exist" and "belongs to someone else".
            raise NotFound("Notification not found.", code="NOTIFICATION_NOT_FOUND")
    row = conn.execute(_SELECT + " WHERE n.notification_id = ?", (notification_id,)).fetchone()
    return notification_view(row)


def mark_all_read(conn: sqlite3.Connection, user_id: str, now: datetime | None = None) -> int:
    with write_transaction(conn):
        cursor = conn.execute(
            """UPDATE notifications SET is_read = 1, read_at = ?
               WHERE user_id = ? AND is_read = 0""",
            (to_db(now or utc_now()), user_id),
        )
        return cursor.rowcount
