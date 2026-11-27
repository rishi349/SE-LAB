import pytest

from app.core.errors import NotFound, PermissionDenied, ValidationFailed
from app.core.money import MAX_DAILY_OUTGOING_PAISE, MAX_SINGLE_TRANSFER_PAISE
from app.modules.admin.service import fund_wallet, search_user_by_id
from tests.helpers import R, balance, ledger_entries, new_key


def fund(conn, admin_id, user_id, amount):
    view, _ = fund_wallet(
        conn,
        admin_user_id=admin_id,
        recipient_user_id=user_id,
        amount_paise=amount,
        idempotency_key=new_key(),
    )
    return view


def test_funding_credits_user_without_debiting_admin(conn, admin, make_user):
    user = make_user()
    assert balance(conn, admin["user_id"]) == 0  # admin can fund from a zero balance
    txn = fund(conn, admin["user_id"], user["user_id"], 750 * R)
    assert txn["type"] == "ADMIN_FUNDING" and txn["status"] == "SUCCESS"
    assert balance(conn, user["user_id"]) == 750 * R
    assert balance(conn, admin["user_id"]) == 0
    entries = ledger_entries(conn, txn["transaction_id"])
    assert [(e["entry_type"], e["amount_paise"]) for e in entries] == [("CREDIT", 750 * R)]


def test_funding_is_not_subject_to_transfer_limits(conn, admin, make_user):
    user = make_user()
    big = MAX_SINGLE_TRANSFER_PAISE * 10
    fund(conn, admin["user_id"], user["user_id"], big)
    fund(conn, admin["user_id"], user["user_id"], MAX_DAILY_OUTGOING_PAISE * 3)
    assert balance(conn, user["user_id"]) == big + MAX_DAILY_OUTGOING_PAISE * 3


@pytest.mark.parametrize("amount", [0, -100])
def test_funding_requires_positive_amount(conn, admin, make_user, amount):
    user = make_user()
    with pytest.raises(ValidationFailed):
        fund(conn, admin["user_id"], user["user_id"], amount)


def test_funding_requires_existing_active_ordinary_user(conn, admin):
    with pytest.raises(NotFound):
        fund(conn, admin["user_id"], "USRDOESNOTEXST", 10 * R)
    with pytest.raises(NotFound):  # admin cannot fund itself
        fund(conn, admin["user_id"], admin["user_id"], 10 * R)


def test_only_admin_can_fund(conn, make_user):
    a, b = make_user(), make_user()
    with pytest.raises(PermissionDenied):
        fund(conn, a["user_id"], b["user_id"], 10 * R)


def test_admin_search_is_by_user_id_only_and_returns_basic_info(conn, admin, make_user):
    user = make_user("Search Me")
    assert search_user_by_id(conn, user["user_id"].lower()) == {
        "user_id": user["user_id"],
        "name": "Search Me",
    }
    with pytest.raises(NotFound):
        search_user_by_id(conn, "user1@example.com")  # an email is not a User ID
    with pytest.raises(NotFound):
        search_user_by_id(conn, user["user_id"][:-2])  # no partial matching
