"""Financial correctness of ordinary transfers, limits and failed attempts."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.clock import IST
from app.core.money import MAX_DAILY_OUTGOING_PAISE, MAX_SINGLE_TRANSFER_PAISE
from app.modules.transfers.service import FailureCode, execute_transfer
from tests.helpers import R, balance, count, ledger_entries, new_key


def send(conn, sender, recipient_id, amount, *, key=None, now=None):
    return execute_transfer(
        conn,
        sender_user_id=sender["user_id"],
        recipient_user_id=recipient_id,
        amount_paise=amount,
        idempotency_key=key or new_key(),
        now=now,
    )


def failure_code(conn, transaction_id):
    return conn.execute(
        "SELECT failure_code FROM transactions WHERE transaction_id = ?", (transaction_id,)
    ).fetchone()["failure_code"]


@pytest.fixture
def pair(make_user, fund):
    a, b = make_user("Alice"), make_user("Bob")
    fund(a["user_id"], 3_00_000 * R)  # ₹3,00,000 so limits, not balance, are tested
    return a, b


def test_successful_transfer_moves_money_with_debit_and_credit(conn, pair):
    a, b = pair
    outcome = send(conn, a, b["user_id"], 1_234 * R + 56)
    txn = outcome.transaction
    assert outcome.succeeded and not outcome.replayed
    assert txn["status"] == "SUCCESS" and txn["direction"] == "OUTGOING"
    assert txn["amount"] == "1234.56"
    assert balance(conn, a["user_id"]) == 3_00_000 * R - 123_456
    assert balance(conn, b["user_id"]) == 123_456

    entries = ledger_entries(conn, txn["transaction_id"])
    assert [(e["entry_type"], e["amount_paise"]) for e in entries] == [
        ("DEBIT", 123_456),
        ("CREDIT", 123_456),
    ]
    assert entries[0]["balance_after_paise"] == balance(conn, a["user_id"])
    assert entries[1]["balance_after_paise"] == balance(conn, b["user_id"])


def test_insufficient_balance_fails_without_moving_money(conn, make_user, fund):
    a, b = make_user(), make_user()
    fund(a["user_id"], 100 * R)
    outcome = send(conn, a, b["user_id"], 100 * R + 1)
    assert not outcome.succeeded
    assert failure_code(conn, outcome.transaction["transaction_id"]) == (
        FailureCode.INSUFFICIENT_BALANCE
    )
    assert balance(conn, a["user_id"]) == 100 * R
    assert balance(conn, b["user_id"]) == 0
    # exact balance works
    assert send(conn, a, b["user_id"], 100 * R).succeeded
    assert balance(conn, a["user_id"]) == 0


@pytest.mark.parametrize("amount", [0, -1, -500 * R])
def test_zero_and_negative_amounts_fail(conn, pair, amount):
    a, b = pair
    outcome = send(conn, a, b["user_id"], amount)
    assert outcome.transaction["status"] == "FAILED"
    assert failure_code(conn, outcome.transaction["transaction_id"]) == FailureCode.INVALID_AMOUNT
    assert balance(conn, b["user_id"]) == 0


def test_single_transfer_limit_is_50000_rupees(conn, pair):
    a, b = pair
    assert send(conn, a, b["user_id"], MAX_SINGLE_TRANSFER_PAISE).succeeded
    over = send(conn, a, b["user_id"], MAX_SINGLE_TRANSFER_PAISE + 1)
    assert not over.succeeded
    assert failure_code(conn, over.transaction["transaction_id"]) == (
        FailureCode.SINGLE_LIMIT_EXCEEDED
    )


def test_daily_limit_counts_only_successful_outgoing_transfers(conn, pair, make_user):
    a, b = pair
    now = datetime(2026, 11, 19, 10, 0, tzinfo=IST)
    # failed attempts do not count towards the limit
    send(conn, a, b["user_id"], MAX_SINGLE_TRANSFER_PAISE + 1, now=now)
    send(conn, a, "USRDOESNOTEXST", 40_000 * R, now=now)
    # an attempt by the recipient in the other direction does not count either
    send(conn, b, a["user_id"], 0, now=now)
    assert send(conn, a, b["user_id"], 50_000 * R, now=now).succeeded
    assert send(conn, a, b["user_id"], 50_000 * R, now=now).succeeded  # exactly ₹1,00,000
    blocked = send(conn, a, b["user_id"], 1, now=now)
    assert not blocked.succeeded
    assert failure_code(conn, blocked.transaction["transaction_id"]) == (
        FailureCode.DAILY_LIMIT_EXCEEDED
    )
    assert balance(conn, b["user_id"]) == MAX_DAILY_OUTGOING_PAISE


def test_daily_limit_resets_at_ist_midnight_not_utc_midnight(conn, pair):
    a, b = pair
    before_midnight = datetime(2026, 11, 19, 23, 59, tzinfo=IST)
    after_midnight = datetime(2026, 11, 20, 0, 1, tzinfo=IST)
    assert send(conn, a, b["user_id"], 50_000 * R, now=before_midnight).succeeded
    assert send(conn, a, b["user_id"], 50_000 * R, now=before_midnight).succeeded
    assert not send(conn, a, b["user_id"], 1 * R, now=before_midnight).succeeded
    assert send(conn, a, b["user_id"], 1 * R, now=after_midnight).succeeded

    # 00:30 IST and 06:00 IST are different UTC dates but the same IST day.
    day = datetime(2026, 11, 22, 0, 30, tzinfo=IST)
    assert (
        day.astimezone(UTC).date() != (day + timedelta(hours=5, minutes=30)).astimezone(UTC).date()
    )
    assert send(conn, a, b["user_id"], 50_000 * R, now=day).succeeded
    assert send(conn, a, b["user_id"], 50_000 * R, now=day + timedelta(hours=1)).succeeded
    assert not send(conn, a, b["user_id"], 1, now=day + timedelta(hours=5, minutes=30)).succeeded


def test_self_transfer_fails(conn, pair):
    a, _ = pair
    outcome = send(conn, a, a["user_id"], 10 * R)
    assert not outcome.succeeded
    assert failure_code(conn, outcome.transaction["transaction_id"]) == FailureCode.SELF_TRANSFER
    assert balance(conn, a["user_id"]) == 3_00_000 * R


def test_nonexistent_recipient_fails_and_is_recorded(conn, pair):
    a, _ = pair
    outcome = send(conn, a, "usrnotarealid", 10 * R)
    txn = outcome.transaction
    assert txn["status"] == "FAILED"
    assert txn["recipient"] == {"user_id": "USRNOTAREALID", "name": None}
    row = conn.execute(
        "SELECT recipient_user_id, failure_code FROM transactions WHERE transaction_id = ?",
        (txn["transaction_id"],),
    ).fetchone()
    assert row["recipient_user_id"] is None
    assert row["failure_code"] == FailureCode.RECIPIENT_NOT_FOUND


def test_admin_is_not_a_valid_transfer_recipient(conn, pair, admin):
    a, _ = pair
    assert not send(conn, a, admin["user_id"], 10 * R).succeeded


def test_failed_attempts_are_persisted_but_create_no_ledger_entries(conn, pair):
    a, b = pair
    entries_before = count(conn, "ledger_entries")
    txns_before = count(conn, "transactions")
    balances_before = (balance(conn, a["user_id"]), balance(conn, b["user_id"]))
    for amount in (0, -1, MAX_SINGLE_TRANSFER_PAISE + 1):
        send(conn, a, b["user_id"], amount)
    send(conn, a, a["user_id"], 1)
    send(conn, a, "USRNOPE", 1)
    assert count(conn, "transactions") == txns_before + 5
    assert count(conn, "ledger_entries") == entries_before
    assert (balance(conn, a["user_id"]), balance(conn, b["user_id"])) == balances_before


def test_failed_transfer_response_has_no_failure_reason(conn, pair):
    a, b = pair
    txn = send(conn, a, b["user_id"], 0).transaction
    assert "failure_code" not in txn
    assert "INVALID_AMOUNT" not in repr(txn)
    assert set(txn) == {
        "transaction_id",
        "type",
        "status",
        "direction",
        "amount_paise",
        "amount",
        "currency",
        "sender",
        "recipient",
        "created_at",
    }


def test_float_amounts_are_refused_by_the_service(conn, pair):
    a, b = pair
    with pytest.raises(TypeError):
        send(conn, a, b["user_id"], 10.5)
    with pytest.raises(TypeError):
        send(conn, a, b["user_id"], True)
