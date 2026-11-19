"""Idempotency: a key, per initiating user, executes at most once."""

import pytest

from app.core.errors import NotFound, ValidationFailed
from app.modules.admin.service import fund_wallet
from app.modules.transfers.service import execute_transfer
from tests.helpers import R, balance, count, new_key


def transfer(conn, sender_id, recipient_id, amount, key):
    return execute_transfer(
        conn,
        sender_user_id=sender_id,
        recipient_user_id=recipient_id,
        amount_paise=amount,
        idempotency_key=key,
    )


def test_same_key_does_not_duplicate_a_transfer(conn, make_user, fund):
    a, b = make_user(), make_user()
    fund(a["user_id"], 1_000 * R)
    key = new_key()
    first = transfer(conn, a["user_id"], b["user_id"], 300 * R, key)
    second = transfer(conn, a["user_id"], b["user_id"], 300 * R, key)
    assert not first.replayed and second.replayed
    assert second.transaction == first.transaction
    assert balance(conn, a["user_id"]) == 700 * R
    assert balance(conn, b["user_id"]) == 300 * R
    assert count(conn, "ledger_entries") == 1 + 2  # funding credit + one transfer


def test_reused_key_returns_original_even_with_a_different_payload(conn, make_user, fund):
    a, b, c = make_user(), make_user(), make_user()
    fund(a["user_id"], 1_000 * R)
    key = new_key()
    original = transfer(conn, a["user_id"], b["user_id"], 100 * R, key)
    replay = transfer(conn, a["user_id"], c["user_id"], 900 * R, key)
    assert replay.replayed
    assert replay.transaction["transaction_id"] == original.transaction["transaction_id"]
    assert balance(conn, c["user_id"]) == 0


def test_failed_attempt_consumes_its_key(conn, make_user, fund):
    a, b = make_user(), make_user()
    key = new_key()
    failed = transfer(conn, a["user_id"], b["user_id"], 100 * R, key)  # no balance yet
    assert failed.transaction["status"] == "FAILED"
    fund(a["user_id"], 1_000 * R)
    retry = transfer(conn, a["user_id"], b["user_id"], 100 * R, key)
    # No automatic retry: the stored failed result is returned; a new key is needed.
    assert retry.replayed and retry.transaction["status"] == "FAILED"
    assert balance(conn, b["user_id"]) == 0
    assert transfer(conn, a["user_id"], b["user_id"], 100 * R, new_key()).succeeded


def test_keys_are_scoped_per_user(conn, make_user, fund):
    a, b = make_user(), make_user()
    fund(a["user_id"], 1_000 * R)
    fund(b["user_id"], 1_000 * R)
    key = "shared-key-123"
    assert transfer(conn, a["user_id"], b["user_id"], 10 * R, key).succeeded
    second = transfer(conn, b["user_id"], a["user_id"], 10 * R, key)
    assert second.succeeded and not second.replayed


def test_admin_funding_is_idempotent(conn, admin, make_user):
    user = make_user()
    key = new_key()
    first, replayed1 = fund_wallet(
        conn,
        admin_user_id=admin["user_id"],
        recipient_user_id=user["user_id"],
        amount_paise=500 * R,
        idempotency_key=key,
    )
    second, replayed2 = fund_wallet(
        conn,
        admin_user_id=admin["user_id"],
        recipient_user_id=user["user_id"],
        amount_paise=500 * R,
        idempotency_key=key,
    )
    assert (replayed1, replayed2) == (False, True)
    assert first == second
    assert balance(conn, user["user_id"]) == 500 * R


def test_rejected_admin_funding_does_not_consume_the_key(conn, admin, make_user):
    user = make_user()
    key = new_key()
    with pytest.raises(ValidationFailed):
        fund_wallet(
            conn,
            admin_user_id=admin["user_id"],
            recipient_user_id=user["user_id"],
            amount_paise=0,
            idempotency_key=key,
        )
    with pytest.raises(NotFound):
        fund_wallet(
            conn,
            admin_user_id=admin["user_id"],
            recipient_user_id="USRNOPE",
            amount_paise=10,
            idempotency_key=key,
        )
    assert count(conn, "transactions") == 0
    view, replayed = fund_wallet(
        conn,
        admin_user_id=admin["user_id"],
        recipient_user_id=user["user_id"],
        amount_paise=10,
        idempotency_key=key,
    )
    assert not replayed and view["status"] == "SUCCESS"
