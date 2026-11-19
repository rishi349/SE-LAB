from tests.api.conftest import API
from tests.helpers import R


def test_history_visibility_and_ownership(api, client, admin_headers):
    a, ha = api.new_user()
    b, hb = api.new_user()
    c, hc = api.new_user()
    api.fund(admin_headers, a["user_id"], 500 * R)
    ok = api.transfer(ha, b["user_id"], 100 * R).json()
    failed = api.transfer(ha, b["user_id"], 0).json()["error"]["details"]["transaction"]

    hist_b = client.get(f"{API}/transactions", headers=hb).json()
    ids_b = [i["transaction_id"] for i in hist_b["items"]]
    assert ids_b == [failed["transaction_id"], ok["transaction_id"]]  # newest first
    assert all(i["direction"] == "INCOMING" for i in hist_b["items"])

    only_failed = client.get(f"{API}/transactions?status=FAILED", headers=ha).json()
    assert [i["transaction_id"] for i in only_failed["items"]] == [failed["transaction_id"]]

    assert client.get(f"{API}/transactions", headers=hc).json()["items"] == []
    other = client.get(f"{API}/transactions/{ok['transaction_id']}", headers=hc)
    assert other.status_code == 404
    mine = client.get(f"{API}/transactions/{ok['transaction_id']}", headers=hb)
    assert mine.status_code == 200
    assert "failure" not in client.get(f"{API}/transactions", headers=ha).text


def test_history_query_validation(api, client):
    _, ha = api.new_user()
    assert client.get(f"{API}/transactions?page_size=500", headers=ha).status_code == 422
    assert client.get(f"{API}/transactions?status=PENDING", headers=ha).status_code == 422
    bad_range = client.get(
        f"{API}/transactions?from_date=2026-11-02&to_date=2026-11-01", headers=ha
    )
    assert bad_range.status_code == 422


def test_admin_endpoints_require_admin(api, client):
    user, headers = api.new_user()
    assert client.get(f"{API}/admin/users/{user['user_id']}", headers=headers).status_code == 403
    funding = client.post(
        f"{API}/admin/fundings",
        json={"recipient_user_id": user["user_id"], "amount_paise": 100},
        headers={**headers, "Idempotency-Key": "abcdefgh-1"},
    )
    assert funding.status_code == 403
    assert client.post(f"{API}/admin/reconciliation-runs", headers=headers).status_code == 403


def test_admin_search_by_user_id_only(api, client, admin_headers):
    user = api.register("Findable")["user"]
    found = client.get(f"{API}/admin/users/{user['user_id']}", headers=admin_headers)
    assert found.status_code == 200
    assert found.json() == {"user_id": user["user_id"], "name": "Findable"}
    # there is no email search: an email is not a valid User ID path parameter
    by_email = client.get(f"{API}/admin/users/{user['email']}", headers=admin_headers)
    assert by_email.status_code in (404, 422)
    query = client.get(f"{API}/admin/users?email={user['email']}", headers=admin_headers)
    assert query.status_code in (404, 405)


def test_admin_funding_api(api, client, admin_headers):
    user, headers = api.new_user()
    txn = api.fund(admin_headers, user["user_id"], 75_000 * R)  # above transfer limits
    assert txn["type"] == "ADMIN_FUNDING"
    assert client.get(f"{API}/wallets/me", headers=headers).json()["balance_paise"] == 75_000 * R
    admin_wallet = client.get(f"{API}/wallets/me", headers=admin_headers).json()
    assert admin_wallet["balance_paise"] == 0
    bad = client.post(
        f"{API}/admin/fundings",
        json={"recipient_user_id": user["user_id"], "amount_paise": 0},
        headers={**admin_headers, "Idempotency-Key": "fund-zero-01"},
    )
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "INVALID_AMOUNT"


def test_reconciliation_api(api, client, admin_headers):
    user, _ = api.new_user()
    api.fund(admin_headers, user["user_id"], 10 * R)
    run = client.post(f"{API}/admin/reconciliation-runs", headers=admin_headers)
    assert run.status_code == 201
    report = run.json()
    assert report["status"] == "COMPLETED_CLEAN" and report["discrepancies"] == []
    listing = client.get(f"{API}/admin/reconciliation-runs", headers=admin_headers).json()
    assert listing["items"][0]["run_id"] == report["run_id"]
    one = client.get(f"{API}/admin/reconciliation-runs/{report['run_id']}", headers=admin_headers)
    assert one.status_code == 200 and one.json() == report
