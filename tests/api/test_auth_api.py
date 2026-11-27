from datetime import UTC, datetime, timedelta

from app.core.security import create_access_token
from tests.api.conftest import API
from tests.conftest import TEST_JWT_SECRET
from tests.helpers import PASSWORD


def test_register_returns_user_and_zero_wallet(client):
    response = client.post(
        f"{API}/auth/register",
        json={"name": "Asha", "email": "asha@example.com", "password": PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "user"
    assert body["wallet"]["balance_paise"] == 0
    assert "password" not in response.text and "password_hash" not in response.text


def test_duplicate_email_is_409(api, client):
    api.register(email="dup@example.com")
    response = client.post(
        f"{API}/auth/register",
        json={"name": "B", "email": "DUP@example.com", "password": PASSWORD},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_cannot_self_register_as_admin(client):
    response = client.post(
        f"{API}/auth/register",
        json={"name": "Eve", "email": "eve@example.com", "password": PASSWORD, "role": "admin"},
    )
    assert response.status_code == 422


def test_validation_errors_do_not_echo_the_password(client):
    response = client.post(
        f"{API}/auth/register",
        json={"name": "A", "email": "bad-email", "password": "tiny"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "tiny" not in response.text


def test_login_and_wrong_password(api, client):
    user = api.register()["user"]
    ok = client.post(f"{API}/auth/login", json={"email": user["email"], "password": PASSWORD})
    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer" and ok.json()["expires_in"] == 3600
    bad = client.post(f"{API}/auth/login", json={"email": user["email"], "password": "nope-nope"})
    unknown = client.post(f"{API}/auth/login", json={"email": "x@example.com", "password": "x"})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()  # no hint whether the email exists


def test_protected_endpoints_require_a_valid_token(api, client):
    user = api.register()["user"]
    assert client.get(f"{API}/wallets/me").status_code == 401
    garbage = client.get(f"{API}/wallets/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert garbage.status_code == 401
    assert garbage.headers["WWW-Authenticate"] == "Bearer"
    expired = create_access_token(
        user["user_id"],
        "user",
        TEST_JWT_SECRET,
        now=datetime.now(UTC) - timedelta(hours=2),
    )
    response = client.get(f"{API}/wallets/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_token_role_claim_cannot_grant_admin(api, client):
    user = api.register()["user"]
    forged_role = create_access_token(user["user_id"], "admin", TEST_JWT_SECRET)
    response = client.get(
        f"{API}/admin/users/{user['user_id']}",
        headers={"Authorization": f"Bearer {forged_role}"},
    )
    assert response.status_code == 403  # role is read from the database


def test_health(client):
    assert client.get(f"{API}/health").json() == {"status": "ok"}


def test_openapi_docs_are_served(client):
    spec = client.get(f"{API}/openapi.json").json()
    assert f"{API}/transfers" in spec["paths"]
    assert client.get("/docs").status_code == 200
