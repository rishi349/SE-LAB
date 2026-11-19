from tests.api.conftest import API
from tests.helpers import R


def test_successful_transfer(api, client, admin_headers):
    a, ha = api.new_user("Alice")
    b, hb = api.new_user("Bob")
    api.fund(admin_headers, a["user_id"], 1_000 * R)
    response = api.transfer(ha, b["user_id"], 400 * R)
    assert response.status_code == 201
    txn = response.json()
    assert txn["status"] == "SUCCESS" and txn["direction"] == "OUTGOING"
    assert client.get(f"{API}/wallets/me", headers=ha).json()["balance_paise"] == 600 * R
    assert client.get(f"{API}/wallets/me", headers=hb).json()["balance_paise"] == 400 * R


def test_failed_transfer_is_recorded_with_generic_error(api, client, admin_headers):
    a, ha = api.new_user()
    b, _ = api.new_user()
    api.fund(admin_headers, a["user_id"], 100 * R)
    responses = [
        api.transfer(ha, b["user_id"], 101 * R),  # insufficient balance
        api.transfer(ha, b["user_id"], 0),  # invalid amount
        api.transfer(ha, b["user_id"], 50_001 * R),  # over single limit
        api.transfer(ha, a["user_id"], 1 * R),  # self transfer
        api.transfer(ha, "USRNOTEXIST000", 1 * R),  # unknown recipient
    ]
    for response in responses:
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "TRANSFER_FAILED"
        assert error["message"] == "The transfer could not be completed."
        assert error["details"]["transaction"]["status"] == "FAILED"
        for reason in ("INSUFFICIENT", "INVALID_AMOUNT", "LIMIT", "SELF", "NOT_FOUND"):
            assert reason not in response.text
    assert client.get(f"{API}/wallets/me", headers=ha).json()["balance_paise"] == 100 * R


def test_idempotent_replay_returns_original(api, client, admin_headers):
    a, ha = api.new_user()
    b, _ = api.new_user()
    api.fund(admin_headers, a["user_id"], 1_000 * R)
    first = api.transfer(ha, b["user_id"], 100 * R, key="retry-key-0001")
    second = api.transfer(ha, b["user_id"], 100 * R, key="retry-key-0001")
    assert first.status_code == second.status_code == 201
    assert second.headers["Idempotent-Replayed"] == "true"
    assert "Idempotent-Replayed" not in first.headers
    assert first.json() == second.json()
    assert client.get(f"{API}/wallets/me", headers=ha).json()["balance_paise"] == 900 * R


def test_idempotency_key_is_required(api, client):
    _, ha = api.new_user()
    b, _ = api.new_user()
    response = client.post(
        f"{API}/transfers", json={"recipient_user_id": b["user_id"], "amount_paise": 1}, headers=ha
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_float_amount_is_rejected_and_not_recorded(api, client):
    _, ha = api.new_user()
    b, _ = api.new_user()
    response = api.transfer(ha, b["user_id"], 10.5)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    history = client.get(f"{API}/transactions", headers=ha).json()
    assert history["pagination"]["total_items"] == 0


def test_admin_cannot_make_ordinary_transfers(api, admin_headers):
    b, _ = api.new_user()
    assert api.transfer(admin_headers, b["user_id"], 1).status_code == 403
