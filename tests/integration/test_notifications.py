"""In-app notifications: who gets what, privacy, idempotency and failure isolation."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import NotFound
from app.modules.notifications import service as notif
from app.modules.reconciliation.service import run_checks
from app.modules.transfers.service import execute_transfer
from app.modules.users.service import purge_expired_accounts, request_account_deletion
from app.modules.wallets.service import get_my_wallet
from tests.helpers import PASSWORD, R, balance, count, new_key


def send(conn, sender, recipient_id, amount, key=None, now=None):
    return execute_transfer(
        conn,
        sender_user_id=sender["user_id"],
        recipient_user_id=recipient_id,
        amount_paise=amount,
        idempotency_key=key or new_key(),
        now=now,
    )


def items(conn, user):
    return notif.list_notifications(conn, user["user_id"])["items"]


@pytest.fixture
def pair(make_user, fund):
    a, b = make_user("Asha"), make_user("Ravi")
    fund(a["user_id"], 10_000 * R)
    return a, b


def test_successful_transfer_notifies_sender_and_recipient(conn, pair):
    a, b = pair
    txn = send(conn, a, b["user_id"], 1_00_000 * R // 100).transaction  # ₹1,000
    sent = items(conn, a)[0]
    received = items(conn, b)[0]
    assert sent["type"] == "TRANSFER_SENT"
    assert sent["message"] == "You sent ₹1,000.00 to Ravi."
    assert received["type"] == "TRANSFER_RECEIVED"
    assert received["message"] == "You received ₹1,000.00 from Asha."
    assert sent["transaction_id"] == received["transaction_id"] == txn["transaction_id"]
    assert not sent["is_read"] and not received["is_read"]


def test_admin_funding_notifies_user_and_not_admin(conn, admin, make_user, fund):
    user = make_user("Pramod")
    fund(user["user_id"], 5_000 * R)
    (only,) = items(conn, user)
    assert only["type"] == "WALLET_FUNDED"
    assert only["message"] == "₹5,000.00 was added to your wallet."
    assert items(conn, admin) == []


def test_failed_transfer_notifies_sender_only_without_reason(conn, pair):
    a, b = pair
    before_b = len(items(conn, b))
    send(conn, a, b["user_id"], 0)  # invalid amount
    send(conn, a, b["user_id"], 60_000 * R)  # over the single limit
    failed = [n for n in items(conn, a) if n["type"] == "TRANSFER_FAILED"]
    assert len(failed) == 2
    assert failed[0]["message"] == "Your transfer of ₹60,000.00 to Ravi could not be completed."
    assert len(items(conn, b)) == before_b  # recipient gets nothing for failed attempts
    text = repr(items(conn, a))
    for reason in ("INVALID", "LIMIT", "INSUFFICIENT", "limit", "balance"):
        assert reason not in text


def test_failed_transfer_to_unknown_recipient_has_no_name(conn, pair):
    a, _ = pair
    send(conn, a, "USRNOBODY00000", 10 * R)
    assert items(conn, a)[0]["message"] == "Your transfer of ₹10.00 could not be completed."


def test_idempotent_replay_creates_no_new_notifications(conn, pair):
    a, b = pair
    key = new_key()
    send(conn, a, b["user_id"], 100 * R, key=key)
    total = count(conn, "notifications")
    replay = send(conn, a, b["user_id"], 100 * R, key=key)
    assert replay.replayed
    assert count(conn, "notifications") == total


def test_notification_failure_never_breaks_a_transfer(conn, pair, caplog):
    a, b = pair
    conn.execute("DROP TABLE notifications")  # simulate the notifier failing
    outcome = send(conn, a, b["user_id"], 300 * R)
    assert outcome.succeeded
    assert balance(conn, a["user_id"]) == 9_700 * R
    assert balance(conn, b["user_id"]) == 300 * R
    assert "could not create notifications" in caplog.text
    assert run_checks(conn).discrepancies == []


def test_newest_first_pagination_and_unread_filter(conn, pair):
    a, b = pair
    base = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
    for i in range(5):
        send(conn, a, b["user_id"], (i + 1) * R, now=base + timedelta(minutes=i))
    page1 = notif.list_notifications(conn, b["user_id"], page=1, page_size=2)
    assert [n["amount_paise"] for n in page1["items"]] == [5 * R, 4 * R]
    assert page1["pagination"]["total_items"] == 5
    assert page1["unread_count"] == 5
    notif.mark_read(conn, b["user_id"], page1["items"][0]["notification_id"])
    unread = notif.list_notifications(conn, b["user_id"], unread_only=True)
    assert unread["pagination"]["total_items"] == 4


def test_mark_read_mark_all_and_unread_count(conn, pair):
    a, b = pair
    send(conn, a, b["user_id"], 10 * R)
    send(conn, a, b["user_id"], 20 * R)
    assert notif.unread_count(conn, b["user_id"]) == 2
    first = items(conn, b)[0]
    marked = notif.mark_read(conn, b["user_id"], first["notification_id"])
    assert marked["is_read"] and marked["read_at"]
    again = notif.mark_read(conn, b["user_id"], first["notification_id"])  # harmless
    assert again["read_at"] == marked["read_at"]
    assert notif.unread_count(conn, b["user_id"]) == 1
    assert notif.mark_all_read(conn, b["user_id"]) == 1
    assert notif.mark_all_read(conn, b["user_id"]) == 0
    assert notif.unread_count(conn, b["user_id"]) == 0


def test_users_cannot_read_or_mark_others_notifications(conn, pair, make_user):
    a, b = pair
    c = make_user("Carol")
    send(conn, a, b["user_id"], 10 * R)
    ravis = items(conn, b)[0]["notification_id"]
    assert items(conn, c) == []
    with pytest.raises(NotFound):
        notif.mark_read(conn, c["user_id"], ravis)
    with pytest.raises(NotFound):
        notif.mark_read(conn, b["user_id"], 999_999)
    assert not items(conn, b)[0]["is_read"]


def test_wallet_response_piggybacks_unread_count(conn, pair):
    a, b = pair
    send(conn, a, b["user_id"], 10 * R)
    assert get_my_wallet(conn, b["user_id"])["unread_notifications"] == 1
    notif.mark_all_read(conn, b["user_id"])
    assert get_my_wallet(conn, b["user_id"])["unread_notifications"] == 0


def test_purge_deletes_own_notifications_and_hides_name_elsewhere(conn, pair):
    a, b = pair
    send(conn, a, b["user_id"], 10_000 * R)  # Asha's balance is now ₹0
    assert items(conn, a)
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    request_account_deletion(conn, a["user_id"], PASSWORD, now=t0)
    purge_expired_accounts(conn, now=t0 + timedelta(days=8))
    remaining = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id = ?", (a["user_id"],)
    ).fetchone()[0]
    assert remaining == 0
    assert items(conn, b)[0]["message"] == "You received ₹10,000.00 from a deleted user."


def test_notifications_do_not_affect_ledger_or_reconciliation(conn, pair):
    a, b = pair
    entries = count(conn, "ledger_entries")
    send(conn, a, b["user_id"], 10 * R)
    send(conn, a, b["user_id"], 0)
    assert count(conn, "ledger_entries") == entries + 2  # one debit + one credit only
    assert run_checks(conn).discrepancies == []


def test_page_size_is_bounded(conn, pair):
    _, b = pair
    with pytest.raises(notif.ValidationFailed):
        notif.list_notifications(conn, b["user_id"], page_size=101)
