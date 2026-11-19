from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import AuthenticationFailed, Conflict
from app.modules.auth.service import login, register_user
from app.modules.transfers.service import execute_transfer
from app.modules.users.service import (
    change_name,
    purge_expired_accounts,
    request_account_deletion,
)
from tests.helpers import PASSWORD, R, balance, count, new_key

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class TestNameChange:
    def test_first_change_allowed_immediately_after_registration(self, conn, make_user):
        user = make_user("Old Name")
        profile = change_name(conn, user["user_id"], "New Name", now=T0)
        assert profile["name"] == "New Name"
        assert profile["next_name_change_allowed_at"] == "2026-03-02T12:00:00.000000Z"

    def test_second_change_blocked_for_60_days(self, conn, make_user):
        user = make_user()
        change_name(conn, user["user_id"], "First", now=T0)
        with pytest.raises(Conflict) as err:
            change_name(conn, user["user_id"], "Second", now=T0 + timedelta(days=59, hours=23))
        assert err.value.code == "NAME_CHANGE_COOLDOWN"
        assert (
            change_name(conn, user["user_id"], "Second", now=T0 + timedelta(days=60))["name"]
            == "Second"
        )

    def test_same_name_does_not_start_cooldown(self, conn, make_user):
        user = make_user("Same")
        profile = change_name(conn, user["user_id"], "  Same ", now=T0)
        assert profile["name_changed_at"] is None


class TestAccountDeletion:
    def test_balance_must_be_settled_first(self, conn, make_user, fund):
        a, b = make_user(), make_user()
        fund(a["user_id"], 100 * R)
        with pytest.raises(Conflict) as err:
            request_account_deletion(conn, a["user_id"], PASSWORD)
        assert err.value.code == "BALANCE_NOT_SETTLED"
        # settle by transferring the balance out
        execute_transfer(
            conn,
            sender_user_id=a["user_id"],
            recipient_user_id=b["user_id"],
            amount_paise=100 * R,
            idempotency_key=new_key(),
        )
        result = request_account_deletion(conn, a["user_id"], PASSWORD, now=T0)
        assert result["status"] == "DEACTIVATED"
        assert result["personal_data_deletion_due_at"] == "2026-01-08T12:00:00.000000Z"

    def test_wrong_password_is_rejected(self, conn, make_user):
        user = make_user()
        with pytest.raises(AuthenticationFailed):
            request_account_deletion(conn, user["user_id"], "not-my-password")

    def test_deactivated_user_cannot_log_in_or_receive(self, conn, settings, make_user, fund):
        a, b = make_user(), make_user()
        fund(b["user_id"], 50 * R)
        request_account_deletion(conn, a["user_id"], PASSWORD)
        with pytest.raises(AuthenticationFailed):
            login(
                conn,
                email="user1@example.com",
                password=PASSWORD,
                jwt_secret=settings.jwt_secret,
                bcrypt_rounds=4,
            )
        outcome = execute_transfer(
            conn,
            sender_user_id=b["user_id"],
            recipient_user_id=a["user_id"],
            amount_paise=10 * R,
            idempotency_key=new_key(),
        )
        assert not outcome.succeeded
        assert balance(conn, a["user_id"]) == 0

    def test_personal_data_deleted_after_7_days_financial_records_kept(self, conn, make_user, fund):
        a, b = make_user(), make_user()
        fund(a["user_id"], 100 * R)
        execute_transfer(
            conn,
            sender_user_id=a["user_id"],
            recipient_user_id=b["user_id"],
            amount_paise=100 * R,
            idempotency_key=new_key(),
        )
        ledger_before, txns_before = count(conn, "ledger_entries"), count(conn, "transactions")
        request_account_deletion(conn, a["user_id"], PASSWORD, now=T0)

        assert purge_expired_accounts(conn, now=T0 + timedelta(days=6, hours=23)) == 0
        assert purge_expired_accounts(conn, now=T0 + timedelta(days=7)) == 1

        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (a["user_id"],)).fetchone()
        assert row["status"] == "DELETED"
        assert (row["name"], row["email"], row["password_hash"]) == (None, None, None)
        assert row["user_id"] == a["user_id"]  # permanent ID kept for the financial record
        assert count(conn, "ledger_entries") == ledger_before
        assert count(conn, "transactions") == txns_before
        assert count(conn, "wallets") >= 2  # wallet row is never deleted

    def test_email_is_reusable_only_after_purge(self, conn, make_user):
        user = make_user()
        request_account_deletion(conn, user["user_id"], PASSWORD, now=T0)
        with pytest.raises(Conflict):
            register_user(
                conn, name="Again", email="user1@example.com", password=PASSWORD, bcrypt_rounds=4
            )
        purge_expired_accounts(conn, now=T0 + timedelta(days=8))
        again = register_user(
            conn, name="Again", email="user1@example.com", password=PASSWORD, bcrypt_rounds=4
        )
        assert again["user"]["user_id"] != user["user_id"]
