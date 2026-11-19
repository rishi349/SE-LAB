"""SQLite connection handling and explicit transaction boundaries.

All money-moving work runs inside ``write_transaction``, which issues ``BEGIN IMMEDIATE``.
That takes SQLite's single write lock *before* any balance is read, so two concurrent
transfers can never both read the same balance and both spend it.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
BUSY_TIMEOUT_MS = 10_000


def connect(database_path: str) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced and manual transaction control."""
    conn = sqlite3.connect(
        database_path,
        timeout=BUSY_TIMEOUT_MS / 1000,
        isolation_level=None,  # we issue BEGIN/COMMIT ourselves
        check_same_thread=False,  # one connection per request; FastAPI may hop threads
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    return conn


def init_db(database_path: str) -> None:
    """Create the database file (if needed) and apply the schema idempotently."""
    parent = Path(database_path).parent
    parent.mkdir(parents=True, exist_ok=True)
    conn = connect(database_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    finally:
        conn.close()


@contextmanager
def write_transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block atomically while holding the database write lock."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


@contextmanager
def read_transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run several reads against one consistent snapshot (used by reconciliation)."""
    conn.execute("BEGIN")
    try:
        yield conn
    finally:
        conn.execute("ROLLBACK")
