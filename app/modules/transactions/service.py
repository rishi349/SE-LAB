"""Transaction history and the public view of a transaction.

``failure_code`` is selected nowhere in this module: internal failure reasons can never
leak into an API response.
"""

from __future__ import annotations

import math
import sqlite3
from datetime import date

from app.core.clock import ist_dates_to_utc_range
from app.core.errors import NotFound, ValidationFailed
from app.core.money import format_rupees

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20

_SELECT = """
SELECT t.transaction_id, t.type, t.status, t.sender_user_id, t.recipient_user_id,
       t.recipient_ref, t.amount_paise, t.created_at,
       s.name AS sender_name, r.name AS recipient_name
FROM transactions t
JOIN users s ON s.user_id = t.sender_user_id
LEFT JOIN users r ON r.user_id = t.recipient_user_id
"""


def transaction_view(row: sqlite3.Row, viewer_user_id: str) -> dict:
    direction = "OUTGOING" if row["sender_user_id"] == viewer_user_id else "INCOMING"
    return {
        "transaction_id": row["transaction_id"],
        "type": row["type"],
        "status": row["status"],
        "direction": direction,
        "amount_paise": row["amount_paise"],
        "amount": format_rupees(row["amount_paise"]),
        "currency": "INR",
        "sender": {"user_id": row["sender_user_id"], "name": row["sender_name"]},
        "recipient": {
            # For a nonexistent recipient we show the ID the sender typed.
            "user_id": row["recipient_user_id"] or row["recipient_ref"],
            "name": row["recipient_name"],
        },
        "created_at": row["created_at"],
    }


def load_transaction_view(
    conn: sqlite3.Connection, transaction_id: str, viewer_user_id: str
) -> dict:
    row = conn.execute(_SELECT + " WHERE t.transaction_id = ?", (transaction_id,)).fetchone()
    if row is None:
        raise NotFound("Transaction not found.", code="TRANSACTION_NOT_FOUND")
    return transaction_view(row, viewer_user_id)


def get_transaction_for_user(
    conn: sqlite3.Connection, viewer_user_id: str, transaction_id: str
) -> dict:
    """Ownership check: users may only see transactions they sent or received."""
    row = conn.execute(
        _SELECT
        + " WHERE t.transaction_id = ? AND (t.sender_user_id = ? OR t.recipient_user_id = ?)",
        (transaction_id, viewer_user_id, viewer_user_id),
    ).fetchone()
    if row is None:
        # Same answer whether it doesn't exist or belongs to someone else.
        raise NotFound("Transaction not found.", code="TRANSACTION_NOT_FOUND")
    return transaction_view(row, viewer_user_id)


def list_history(
    conn: sqlite3.Connection,
    viewer_user_id: str,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    status: str | None = None,
    direction: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict:
    if page < 1 or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValidationFailed(f"page must be >= 1 and page_size between 1 and {MAX_PAGE_SIZE}.")
    if from_date and to_date and from_date > to_date:
        raise ValidationFailed("from_date must not be after to_date.", code="INVALID_DATE_RANGE")
    if status not in (None, "SUCCESS", "FAILED"):
        raise ValidationFailed("status must be SUCCESS or FAILED.")
    if direction not in (None, "INCOMING", "OUTGOING"):
        raise ValidationFailed("direction must be INCOMING or OUTGOING.")

    where = ["(t.sender_user_id = :me OR t.recipient_user_id = :me)"]
    params: dict[str, object] = {"me": viewer_user_id}
    if status:
        where.append("t.status = :status")
        params["status"] = status
    if direction == "OUTGOING":
        where.append("t.sender_user_id = :me")
    elif direction == "INCOMING":
        where.append("t.recipient_user_id = :me AND t.sender_user_id <> :me")
    start, end = ist_dates_to_utc_range(from_date, to_date)
    if start:
        where.append("t.created_at >= :start")
        params["start"] = start
    if end:
        where.append("t.created_at < :end")
        params["end"] = end

    clause = " WHERE " + " AND ".join(where)
    total = conn.execute("SELECT COUNT(*) AS n FROM transactions t" + clause, params).fetchone()[
        "n"
    ]
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    rows = conn.execute(
        _SELECT + clause + " ORDER BY t.created_at DESC, t.rowid DESC LIMIT :limit OFFSET :offset",
        params,
    ).fetchall()
    return {
        "items": [transaction_view(row, viewer_user_id) for row in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": math.ceil(total / page_size) if total else 0,
        },
    }
