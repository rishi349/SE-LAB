import pytest

from app.core.errors import AuthenticationFailed, Conflict
from app.modules.auth.service import login, register_user
from app.modules.wallets.service import get_my_wallet
from tests.helpers import PASSWORD, count


def test_registration_creates_user_and_zero_wallet(conn, settings):
    result = register_user(
        conn, name="Asha", email="asha@example.com", password=PASSWORD, bcrypt_rounds=4
    )
    user, wallet = result["user"], result["wallet"]
    assert user["role"] == "user"
    assert user["user_id"].startswith("USR")
    assert wallet["user_id"] == user["user_id"]
    assert wallet["balance_paise"] == 0
    assert get_my_wallet(conn, user["user_id"])["balance"] == "0.00"
    # registration does not start the name-change cooldown
    assert user["name_changed_at"] is None


def test_duplicate_email_rejected_without_creating_anything(conn):
    register_user(conn, name="A", email="dup@example.com", password=PASSWORD, bcrypt_rounds=4)
    users, wallets = count(conn, "users"), count(conn, "wallets")
    with pytest.raises(Conflict) as err:
        register_user(conn, name="B", email="DUP@example.com", password=PASSWORD, bcrypt_rounds=4)
    assert err.value.code == "EMAIL_ALREADY_REGISTERED"
    assert (count(conn, "users"), count(conn, "wallets")) == (users, wallets)


def test_every_user_has_exactly_one_wallet(conn, make_user, admin):
    for _ in range(5):
        make_user()
    rows = conn.execute(
        "SELECT u.user_id, COUNT(w.wallet_id) AS n FROM users u "
        "LEFT JOIN wallets w ON w.user_id = u.user_id GROUP BY u.user_id"
    ).fetchall()
    assert len(rows) == 6
    assert all(r["n"] == 1 for r in rows)


def test_login_success_and_failure(conn, settings, make_user):
    make_user()
    token = login(
        conn,
        email="user1@example.com",
        password=PASSWORD,
        jwt_secret=settings.jwt_secret,
        bcrypt_rounds=4,
    )
    assert token["token_type"] == "bearer" and token["expires_in"] == 3600
    for email, pw in (("user1@example.com", "wrong-pass"), ("nobody@example.com", PASSWORD)):
        with pytest.raises(AuthenticationFailed) as err:
            login(conn, email=email, password=pw, jwt_secret=settings.jwt_secret, bcrypt_rounds=4)
        assert err.value.code == "INVALID_CREDENTIALS"


def test_admin_is_a_separate_role_with_a_zero_wallet(conn, admin):
    assert admin["role"] == "admin"
    assert get_my_wallet(conn, admin["user_id"])["balance_paise"] == 0
