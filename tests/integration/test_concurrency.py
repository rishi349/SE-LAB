"""Concurrent transfers: no double spending, no negative balances, no duplicates."""

import threading
from concurrent.futures import ThreadPoolExecutor

from app.db.connection import connect
from app.modules.reconciliation.service import run_checks
from app.modules.transfers.service import execute_transfer
from tests.helpers import R, balance, count


def run_parallel(settings, jobs):
    """Run each (sender, recipient, amount, key) job on its own connection, all at once."""
    barrier = threading.Barrier(len(jobs))

    def worker(job):
        sender, recipient, amount, key = job
        local = connect(settings.database_path)
        try:
            barrier.wait()
            return execute_transfer(
                local,
                sender_user_id=sender,
                recipient_user_id=recipient,
                amount_paise=amount,
                idempotency_key=key,
            )
        finally:
            local.close()

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        return list(pool.map(worker, jobs))


def test_concurrent_transfers_cannot_double_spend(settings, conn, make_user, fund):
    a, b = make_user(), make_user()
    fund(a["user_id"], 30_000 * R)
    jobs = [(a["user_id"], b["user_id"], 5_000 * R, f"conc-{i:04d}") for i in range(12)]
    outcomes = run_parallel(settings, jobs)

    assert sum(o.succeeded for o in outcomes) == 6  # 6 x ₹5,000 = ₹30,000
    assert balance(conn, a["user_id"]) == 0
    assert balance(conn, b["user_id"]) == 30_000 * R
    assert count(conn, "transactions") == 1 + 12
    assert run_checks(conn).discrepancies == []


def test_concurrent_retries_with_one_key_execute_once(settings, conn, make_user, fund):
    a, b = make_user(), make_user()
    fund(a["user_id"], 10_000 * R)
    jobs = [(a["user_id"], b["user_id"], 1_000 * R, "same-key-everywhere")] * 8
    outcomes = run_parallel(settings, jobs)

    assert len({o.transaction["transaction_id"] for o in outcomes}) == 1
    assert sum(not o.replayed for o in outcomes) == 1
    assert balance(conn, b["user_id"]) == 1_000 * R
    assert run_checks(conn).discrepancies == []


def test_crossing_transfers_keep_totals_and_ledger_consistent(settings, conn, make_user, fund):
    a, b = make_user(), make_user()
    fund(a["user_id"], 5_000 * R)
    fund(b["user_id"], 5_000 * R)
    jobs = []
    for i in range(10):
        jobs.append((a["user_id"], b["user_id"], 700 * R, f"ab-{i:04d}"))
        jobs.append((b["user_id"], a["user_id"], 300 * R, f"ba-{i:04d}"))
    outcomes = run_parallel(settings, jobs)

    assert all(o.transaction["status"] in ("SUCCESS", "FAILED") for o in outcomes)
    assert balance(conn, a["user_id"]) + balance(conn, b["user_id"]) == 10_000 * R
    assert balance(conn, a["user_id"]) >= 0 and balance(conn, b["user_id"]) >= 0
    assert run_checks(conn).discrepancies == []
