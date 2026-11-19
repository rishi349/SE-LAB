import sqlite3

import pytest

from app.modules.reconciliation import service as recon
from app.modules.transfers.service import execute_transfer
from tests.helpers import R, new_key, snapshot


@pytest.fixture
def activity(conn, make_user, fund):
    a, b = make_user(), make_user()
    fund(a["user_id"], 1_000 * R)
    ok = execute_transfer(
        conn,
        sender_user_id=a["user_id"],
        recipient_user_id=b["user_id"],
        amount_paise=250 * R,
        idempotency_key=new_key(),
    ).transaction
    failed = execute_transfer(
        conn,
        sender_user_id=a["user_id"],
        recipient_user_id=b["user_id"],
        amount_paise=0,
        idempotency_key=new_key(),
    ).transaction
    return a, b, ok, failed


def checks(report):
    return {d["check_name"] for d in report["discrepancies"]}


def test_clean_run(conn, admin, activity):
    report = recon.run_reconciliation(conn, triggered_by=admin["user_id"])
    assert report["status"] == "COMPLETED_CLEAN"
    assert report["discrepancy_count"] == 0
    assert report["wallets_checked"] == 3  # admin + 2 users
    assert report["transactions_checked"] == 3
    assert report["failure_detail"] is None


def test_wallet_balance_tampering_is_detected_not_repaired(conn, admin, activity):
    a, *_ = activity
    conn.execute(
        "UPDATE wallets SET balance_paise = balance_paise + 1 WHERE user_id = ?", (a["user_id"],)
    )
    before = snapshot(conn)
    report = recon.run_reconciliation(conn, triggered_by=admin["user_id"])
    assert report["status"] == "COMPLETED_WITH_DISCREPANCIES"
    assert {recon.Check.WALLET_LEDGER_MISMATCH, recon.Check.SYSTEM_TOTAL} <= checks(report)
    assert snapshot(conn) == before  # read-only: nothing was "fixed"


def test_unbalanced_transfer_is_detected(conn, admin, activity):
    _, _, ok, _ = activity
    conn.execute("DROP TRIGGER trg_ledger_no_update")  # simulate corruption
    conn.execute(
        "UPDATE ledger_entries SET amount_paise = 1 WHERE transaction_id = ? "
        "AND entry_type = 'CREDIT'",
        (ok["transaction_id"],),
    )
    report = recon.run_reconciliation(conn, triggered_by=admin["user_id"])
    assert {recon.Check.TRANSFER_INTEGRITY, recon.Check.DEBIT_CREDIT_BALANCE} <= checks(report)


def test_failed_transaction_with_ledger_entry_is_detected(conn, admin, activity):
    a, _, _, failed = activity
    wallet = conn.execute(
        "SELECT wallet_id FROM wallets WHERE user_id = ?", (a["user_id"],)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO ledger_entries (transaction_id, wallet_id, entry_type, amount_paise,"
        " balance_after_paise, created_at) VALUES (?, ?, 'CREDIT', 5, 0, 't')",
        (failed["transaction_id"], wallet),
    )
    report = recon.run_reconciliation(conn, triggered_by=admin["user_id"])
    assert recon.Check.STATUS_VS_RECORDS in checks(report)


def test_admin_funding_with_debit_is_detected(conn, admin, make_user, fund):
    user = make_user()
    txn = fund(user["user_id"], 100 * R)
    admin_wallet = conn.execute(
        "SELECT wallet_id FROM wallets WHERE user_id = ?", (admin["user_id"],)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO ledger_entries (transaction_id, wallet_id, entry_type, amount_paise,"
        " balance_after_paise, created_at) VALUES (?, ?, 'DEBIT', ?, 0, 't')",
        (txn["transaction_id"], admin_wallet, 100 * R),
    )
    report = recon.run_reconciliation(conn, triggered_by=admin["user_id"])
    assert recon.Check.ADMIN_FUNDING_INTEGRITY in checks(report)


def test_run_that_crashes_is_recorded_as_failed(conn, admin, monkeypatch):
    def boom(_conn):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(recon, "run_checks", boom)
    report = recon.run_reconciliation(conn, triggered_by=admin["user_id"])
    assert report["status"] == "FAILED"
    assert "disk on fire" in report["failure_detail"]


def test_reports_are_retained_listed_and_immutable(conn, admin, activity):
    first = recon.run_reconciliation(conn, triggered_by=admin["user_id"])
    second = recon.run_reconciliation(conn, triggered_by=admin["user_id"])
    assert first["run_id"] != second["run_id"]
    listing = recon.list_runs(conn)
    assert [r["run_id"] for r in listing["items"]] == [second["run_id"], first["run_id"]]
    assert recon.get_report(conn, first["run_id"]) == first
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE reconciliation_runs SET status = 'FAILED'")
    with pytest.raises(recon.NotFound):
        recon.get_report(conn, "RECDOESNOTEXIST")
