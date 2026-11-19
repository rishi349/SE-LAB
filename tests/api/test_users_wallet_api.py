from tests.api.conftest import API
from tests.helpers import PASSWORD, R


def test_view_own_profile_and_wallet(api, client):
    user, headers = api.new_user("Ravi")
    profile = client.get(f"{API}/users/me", headers=headers).json()
    assert profile["user_id"] == user["user_id"] and profile["name"] == "Ravi"
    wallet = client.get(f"{API}/wallets/me", headers=headers).json()
    assert wallet["balance_paise"] == 0 and wallet["balance"] == "0.00"


def test_name_change_then_cooldown(api, client):
    _, headers = api.new_user()
    first = client.patch(f"{API}/users/me", json={"name": "Changed"}, headers=headers)
    assert first.status_code == 200 and first.json()["name"] == "Changed"
    second = client.patch(f"{API}/users/me", json={"name": "Again"}, headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "NAME_CHANGE_COOLDOWN"


def test_email_and_user_id_are_not_editable(api, client):
    _, headers = api.new_user()
    for field in ("email", "user_id", "role"):
        response = client.patch(f"{API}/users/me", json={"name": "X", field: "y"}, headers=headers)
        assert response.status_code == 422


def test_recipient_lookup_returns_only_id_and_name(api, client):
    other = api.register("Target")["user"]
    _, headers = api.new_user()
    response = client.get(f"{API}/users/{other['user_id']}", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"user_id": other["user_id"], "name": "Target"}
    missing = client.get(f"{API}/users/USR0000000000", headers=headers)
    assert missing.status_code == 404


def test_account_deletion_flow(api, client, admin_headers):
    user, headers = api.new_user()
    other, _ = api.new_user()
    api.fund(admin_headers, user["user_id"], 10 * R)
    blocked = client.post(
        f"{API}/users/me/deletion-request", json={"password": PASSWORD}, headers=headers
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "BALANCE_NOT_SETTLED"

    assert api.transfer(headers, other["user_id"], 10 * R).status_code == 201
    done = client.post(
        f"{API}/users/me/deletion-request", json={"password": PASSWORD}, headers=headers
    )
    assert done.status_code == 202 and done.json()["status"] == "DEACTIVATED"
    # existing token stops working and login is refused
    assert client.get(f"{API}/wallets/me", headers=headers).status_code == 401
    login = client.post(f"{API}/auth/login", json={"email": user["email"], "password": PASSWORD})
    assert login.status_code == 401


def test_admin_cannot_delete_itself_via_api(client, admin_headers):
    response = client.post(
        f"{API}/users/me/deletion-request", json={"password": PASSWORD}, headers=admin_headers
    )
    assert response.status_code == 403
