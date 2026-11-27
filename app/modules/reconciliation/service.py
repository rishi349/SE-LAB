"""Reconciliation: read-only integrity checks with stored, immutable reports.

Reconciliation never changes wallets, transactions or ledger entries. It reads one
consistent snapshot, records what it found in its own report tables, and stops. Fixing a
discrepancy is a deliberate human decision outside this module.
"""

from __future__ import annotations

import logging
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from app.core.clock import to_db, utc_now
from app.core.errors import NotFound, ValidationFailed
from app.core.ids import new_run_id
from app.db.connection import read_transaction, write_transaction

logger = logging.getLogger("app.reconciliation")

COMPLETED_CLEAN = "COMPLETED_CLEAN"
COMPLETED_WITH_DISCREPANCIES = "COMPLETED_WITH_DISCREPANCIES"
FAILED = "FAILED"


class Check:
    WALLET_LEDGER_MISMATCH = "WALLET_BALANCE_VS_LEDGER"
    NEGATIVE_BALANCE = "NEGATIVE_WALLET_BALANCE"
    TRANSFER_INTEGRITY = "TRANSFER_INTEGRITY"
    DEBIT_CREDIT_BALANCE = "DEBIT_CREDIT_BALANCE"
    STATUS_VS_RECORDS = "STATUS_VS_FINANCIAL_RECORDS"
    ADMIN_FUNDING_INTEGRITY = "ADMIN_FUNDING_INTEGRITY"
    SYSTEM_TOTAL = "SYSTEM_TOTAL_VS_FUNDING"


@dataclass(frozen=True)
class Discrepancy:
    check_name: str
    entity_type: str
    entity_id: str
    expected: str | None
    actual: str | None
    detail: str


@dataclass(frozen=True)
class CheckResult:
    wallets_checked: int
    transactions_checked: int
    discrepancies: list[Discrepancy]


def _check_wallets(conn: sqlite3.Connection, found: list[Discrepancy]) -> tuple[int, dict, int]:
    rows = conn.execute(
        """SELECT w.wallet_id, w.user_id, w.balance_paise,
                  COALESCE(SUM(CASE le.entry_type WHEN 'CREDIT' THEN le.amount_paise
                                                  WHEN 'DEBIT' THEN -le.amount_paise END), 0)
                      AS ledger_balance
           FROM wallets w LEFT JOIN ledger_entries le ON le.wallet_id = w.wallet_id
           GROUP BY w.wallet_id ORDER BY w.wallet_id"""
    ).fetchall()
    wallet_of_user = {}
    total_balance = 0
    for row in rows:
        wallet_of_user[row["user_id"]] = row["wallet_id"]
        total_balance += row["balance_paise"]
        if row["balance_paise"] != row["ledger_balance"]:
            found.append(
                Discrepancy(
                    Check.WALLET_LEDGER_MISMATCH,
                    "wallet",
                    row["wallet_id"],
                    str(row["ledger_balance"]),
                    str(row["balance_paise"]),
                    "Stored wallet balance differs from the balance derived from ledger entries.",
                )
            )
        if row["balance_paise"] < 0:
            found.append(
                Discrepancy(
                    Check.NEGATIVE_BALANCE,
                    "wallet",
                    row["wallet_id"],
                    ">= 0",
                    str(row["balance_paise"]),
                    "Wallet balance is negative.",
                )
            )
    return len(rows), wallet_of_user, total_balance


def _check_transactions(
    conn: sqlite3.Connection, wallet_of_user: dict, found: list[Discrepancy]
) -> tuple[int, int]:
    entries: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for entry in conn.execute(
        "SELECT transaction_id, wallet_id, entry_type, amount_paise FROM ledger_entries"
    ):
        entries[entry["transaction_id"]].append(entry)
    roles = {r["user_id"]: r["role"] for r in conn.execute("SELECT user_id, role FROM users")}

    txns = conn.execute(
        """SELECT transaction_id, type, status, sender_user_id, recipient_user_id, amount_paise
           FROM transactions ORDER BY created_at"""
    ).fetchall()
    funded_total = 0
    for txn in txns:
        tid = txn["transaction_id"]
        own = entries.get(tid, [])
        debits = [e for e in own if e["entry_type"] == "DEBIT"]
        credits = [e for e in own if e["entry_type"] == "CREDIT"]

        def add(check: str, expected: str, actual: str, detail: str, tid: str = tid) -> None:
            found.append(Discrepancy(check, "transaction", tid, expected, actual, detail))

        if txn["status"] == "FAILED":
            if own:
                add(
                    Check.STATUS_VS_RECORDS,
                    "0 ledger entries",
                    f"{len(own)} ledger entries",
                    "A failed transaction has ledger entries (money may have moved).",
                )
            continue
        if not own:
            add(
                Check.STATUS_VS_RECORDS,
                "ledger entries",
                "none",
                "A successful transaction has no ledger entries.",
            )
            continue

        amount = txn["amount_paise"]
        recipient_wallet = wallet_of_user.get(txn["recipient_user_id"])
        if txn["type"] == "TRANSFER":
            sender_wallet = wallet_of_user.get(txn["sender_user_id"])
            ok = (
                len(debits) == 1
                and len(credits) == 1
                and debits[0]["wallet_id"] == sender_wallet
                and credits[0]["wallet_id"] == recipient_wallet
                and debits[0]["amount_paise"] == amount
                and credits[0]["amount_paise"] == amount
                and txn["sender_user_id"] != txn["recipient_user_id"]
            )
            if not ok:
                add(
                    Check.TRANSFER_INTEGRITY,
                    f"1 DEBIT on sender wallet and 1 CREDIT on recipient wallet of {amount}",
                    f"{len(debits)} DEBIT, {len(credits)} CREDIT",
                    "Transfer ledger entries do not match the transaction.",
                )
            debit_sum = sum(e["amount_paise"] for e in debits)
            credit_sum = sum(e["amount_paise"] for e in credits)
            if debit_sum != credit_sum:
                add(
                    Check.DEBIT_CREDIT_BALANCE,
                    str(debit_sum),
                    str(credit_sum),
                    "Debits and credits of this transfer do not balance.",
                )
        else:  # ADMIN_FUNDING
            funded_total += amount
            ok = (
                not debits
                and len(credits) == 1
                and credits[0]["wallet_id"] == recipient_wallet
                and credits[0]["amount_paise"] == amount
                and roles.get(txn["sender_user_id"]) == "admin"
            )
            if not ok:
                add(
                    Check.ADMIN_FUNDING_INTEGRITY,
                    f"exactly 1 CREDIT of {amount} on recipient wallet, no DEBIT, admin sender",
                    f"{len(debits)} DEBIT, {len(credits)} CREDIT",
                    "Admin funding records do not match the admin-funding model.",
                )
    return len(txns), funded_total


def run_checks(conn: sqlite3.Connection) -> CheckResult:
    found: list[Discrepancy] = []
    with read_transaction(conn):
        wallets_checked, wallet_of_user, total_balance = _check_wallets(conn, found)
        txns_checked, funded_total = _check_transactions(conn, wallet_of_user, found)
    # Money only enters the system through admin funding, so all balances together must
    # equal everything ever funded.
    if total_balance != funded_total:
        found.append(
            Discrepancy(
                Check.SYSTEM_TOTAL,
                "system",
                "ALL_WALLETS",
                str(funded_total),
                str(total_balance),
                "Sum of all wallet balances differs from total successful admin funding.",
            )
        )
    return CheckResult(wallets_checked, txns_checked, found)


def run_reconciliation(
    conn: sqlite3.Connection, *, triggered_by: str, now: datetime | None = None
) -> dict:
    run_id = new_run_id()
    started_at = to_db(now or utc_now())
    failure_detail = None
    try:
        result = run_checks(conn)
        status = COMPLETED_WITH_DISCREPANCIES if result.discrepancies else COMPLETED_CLEAN
    except Exception as exc:  # the run itself broke; record it as FAILED
        logger.exception("reconciliation run %s failed", run_id)
        result = CheckResult(0, 0, [])
        status = FAILED
        failure_detail = f"{type(exc).__name__}: {exc}"[:1000]
    completed_at = to_db(utc_now())

    with write_transaction(conn):
        conn.execute(
            """INSERT INTO reconciliation_runs (run_id, status, triggered_by, started_at,
                   completed_at, wallets_checked, transactions_checked, discrepancy_count,
                   failure_detail)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                status,
                triggered_by,
                started_at,
                completed_at,
                result.wallets_checked,
                result.transactions_checked,
                len(result.discrepancies),
                failure_detail,
            ),
        )
        conn.executemany(
            """INSERT INTO reconciliation_discrepancies (run_id, check_name, entity_type,
                   entity_id, expected, actual, detail)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (run_id, d.check_name, d.entity_type, d.entity_id, d.expected, d.actual, d.detail)
                for d in result.discrepancies
            ],
        )
    return get_report(conn, run_id)


def _summary(row: sqlite3.Row) -> dict:
    return {
        key: row[key]
        for key in (
            "run_id",
            "status",
            "triggered_by",
            "started_at",
            "completed_at",
            "wallets_checked",
            "transactions_checked",
            "discrepancy_count",
            "failure_detail",
        )
    }


def get_report(conn: sqlite3.Connection, run_id: str) -> dict:
    row = conn.execute("SELECT * FROM reconciliation_runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        raise NotFound("Reconciliation run not found.", code="RECONCILIATION_RUN_NOT_FOUND")
    report = _summary(row)
    report["discrepancies"] = [
        {
            key: d[key]
            for key in ("check_name", "entity_type", "entity_id", "expected", "actual", "detail")
        }
        for d in conn.execute(
            "SELECT * FROM reconciliation_discrepancies WHERE run_id = ? ORDER BY discrepancy_id",
            (run_id,),
        )
    ]
    return report


def list_runs(conn: sqlite3.Connection, *, page: int = 1, page_size: int = 20) -> dict:
    if page < 1 or not 1 <= page_size <= 100:
        raise ValidationFailed("page must be >= 1 and page_size between 1 and 100.")
    total = conn.execute("SELECT COUNT(*) AS n FROM reconciliation_runs").fetchone()["n"]
    rows = conn.execute(
        """SELECT * FROM reconciliation_runs ORDER BY started_at DESC, rowid DESC
           LIMIT ? OFFSET ?""",
        (page_size, (page - 1) * page_size),
    ).fetchall()
    return {
        "items": [_summary(r) for r in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": math.ceil(total / page_size) if total else 0,
        },
    }
