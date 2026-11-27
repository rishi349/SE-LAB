from datetime import date, datetime, timedelta

import pytest

from app.core.clock import IST
from app.core.errors import NotFound, ValidationFailed
from app.modules.transactions.service import get_transaction_for_user, list_history
from app.modules.transfers.service import execute_transfer
from tests.helpers import R, new_key


def send(conn, sender, recipient_id, amount, now=None):
    return execute_transfer(
        conn,
        sender_user_id=sender["user_id"],
        recipient_user_id=recipient_id,
        amount_paise=amount,
        idempotency_key=new_key(),
        now=now,
    ).transaction


@pytest.fixture
def trio(make_user, fund):
    a, b, c = make_user("Alice"), make_user("Bob"), make_user("Carol")
    fund(a["user_id"], 10_000 * R)
    return a, b, c


def ids(page):
    return [item["transaction_id"] for item in page["items"]]


def test_history_is_newest_first_with_direction(conn, trio):
    a, b, _ = trio
    base = datetime(2026, 11, 1, 9, 0, tzinfo=IST)
    t1 = send(conn, a, b["user_id"], 100 * R, now=base)
    t2 = send(conn, a, b["user_id"], 200 * R, now=base + timedelta(minutes=1))
    page_a = list_history(conn, a["user_id"], direction="OUTGOING")
    assert ids(page_a) == [t2["transaction_id"], t1["transaction_id"]]
    page_b = list_history(conn, b["user_id"])
    assert ids(page_b) == [t2["transaction_id"], t1["transaction_id"]]
    assert {i["direction"] for i in page_b["items"]} == {"INCOMING"}
    first = page_b["items"][0]
    assert first["sender"] == {"user_id": a["user_id"], "name": "Alice"}
    assert first["recipient"] == {"user_id": b["user_id"], "name": "Bob"}
    assert first["amount_paise"] == 200 * R and first["status"] == "SUCCESS"


def test_pagination_is_bounded(conn, trio):
    a, b, _ = trio
    for _ in range(7):
        send(conn, a, b["user_id"], 1 * R)
    page1 = list_history(conn, b["user_id"], page=1, page_size=3)
    page3 = list_history(conn, b["user_id"], page=3, page_size=3)
    assert len(page1["items"]) == 3 and len(page3["items"]) == 1
    assert page1["pagination"] == {"page": 1, "page_size": 3, "total_items": 7, "total_pages": 3}
    assert not set(ids(page1)) & set(ids(page3))
    with pytest.raises(ValidationFailed):
        list_history(conn, b["user_id"], page_size=101)
    with pytest.raises(ValidationFailed):
        list_history(conn, b["user_id"], page=0)


def test_status_direction_and_date_filters(conn, trio):
    a, b, _ = trio
    nov1 = datetime(2026, 11, 1, 23, 50, tzinfo=IST)  # late on 1 Nov IST (still 1 Nov)
    nov2 = datetime(2026, 11, 2, 0, 10, tzinfo=IST)
    ok = send(conn, a, b["user_id"], 100 * R, now=nov1)
    failed = send(conn, a, b["user_id"], 0, now=nov2)
    back = send(conn, b, a["user_id"], 50 * R, now=nov2)

    assert ids(list_history(conn, a["user_id"], status="FAILED")) == [failed["transaction_id"]]
    incoming = list_history(conn, a["user_id"], direction="INCOMING")
    assert back["transaction_id"] in ids(incoming)
    assert ok["transaction_id"] not in ids(incoming)
    only_nov1 = list_history(
        conn, a["user_id"], from_date=date(2026, 11, 1), to_date=date(2026, 11, 1)
    )
    assert ids(only_nov1) == [ok["transaction_id"]]
    with pytest.raises(ValidationFailed):
        list_history(conn, a["user_id"], from_date=date(2026, 11, 2), to_date=date(2026, 11, 1))


def test_failed_attempt_with_valid_recipient_is_visible_to_both(conn, trio):
    a, b, _ = trio
    failed = send(conn, a, b["user_id"], 999_999 * R)  # over the single limit
    for viewer, direction in ((a, "OUTGOING"), (b, "INCOMING")):
        item = get_transaction_for_user(conn, viewer["user_id"], failed["transaction_id"])
        assert item["status"] == "FAILED" and item["direction"] == direction
        assert item["amount_paise"] == 999_999 * R


def test_failed_attempt_to_nonexistent_recipient_is_visible_to_sender_only(conn, trio):
    a, b, _ = trio
    failed = send(conn, a, "USRGHOSTUSER00", 5 * R)
    assert failed["transaction_id"] in ids(list_history(conn, a["user_id"]))
    assert failed["transaction_id"] not in ids(list_history(conn, b["user_id"]))


def test_users_only_see_their_own_transactions(conn, trio):
    a, b, c = trio
    txn = send(conn, a, b["user_id"], 10 * R)
    assert ids(list_history(conn, c["user_id"])) == []
    with pytest.raises(NotFound):
        get_transaction_for_user(conn, c["user_id"], txn["transaction_id"])


def test_history_never_contains_failure_reasons(conn, trio):
    a, b, _ = trio
    send(conn, a, b["user_id"], 0)
    send(conn, a, a["user_id"], 10)
    send(conn, a, "USRNOBODY00000", 10)
    text = repr(list_history(conn, a["user_id"]))
    for secret in ("failure", "INVALID_AMOUNT", "SELF_TRANSFER", "RECIPIENT_NOT_FOUND"):
        assert secret not in text
