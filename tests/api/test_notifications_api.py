from tests.api.conftest import API
from tests.helpers import R


def test_notification_endpoints(api, client, admin_headers):
    a, ha = api.new_user("Asha")
    b, hb = api.new_user("Ravi")
    api.fund(admin_headers, a["user_id"], 1_000 * R)
    assert api.transfer(ha, b["user_id"], 250 * R).status_code == 201

    count = client.get(f"{API}/notifications/unread-count", headers=hb)
    assert count.status_code == 200 and count.json() == {"unread_count": 1}
    assert client.get(f"{API}/wallets/me", headers=hb).json()["unread_notifications"] == 1

    page = client.get(f"{API}/notifications", headers=hb).json()
    item = page["items"][0]
    assert item["type"] == "TRANSFER_RECEIVED"
    assert item["message"] == "You received ₹250.00 from Asha."
    assert page["unread_count"] == 1 and page["pagination"]["total_items"] == 1

    read = client.patch(f"{API}/notifications/{item['notification_id']}/read", headers=hb)
    assert read.status_code == 200 and read.json()["is_read"] is True
    unread = client.get(f"{API}/notifications?unread_only=true", headers=hb).json()
    assert unread["items"] == []

    asha = client.get(f"{API}/notifications", headers=ha).json()
    assert [n["type"] for n in asha["items"]] == ["TRANSFER_SENT", "WALLET_FUNDED"]
    done = client.post(f"{API}/notifications/read-all", headers=ha)
    assert done.status_code == 200 and done.json() == {"updated": 2}


def test_notifications_are_private(api, client, admin_headers):
    a, ha = api.new_user()
    _, hc = api.new_user()
    api.fund(admin_headers, a["user_id"], 10 * R)
    nid = client.get(f"{API}/notifications", headers=ha).json()["items"][0]["notification_id"]
    other = client.patch(f"{API}/notifications/{nid}/read", headers=hc)
    assert other.status_code == 404
    assert other.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"
    assert client.get(f"{API}/notifications", headers=hc).json()["items"] == []


def test_notifications_require_auth_and_validate_input(api, client):
    assert client.get(f"{API}/notifications").status_code == 401
    _, headers = api.new_user()
    assert client.get(f"{API}/notifications?page_size=500", headers=headers).status_code == 422
    assert client.patch(f"{API}/notifications/0/read", headers=headers).status_code == 422


def test_failed_transfer_notification_reaches_sender_only(api, client, admin_headers):
    a, ha = api.new_user()
    b, hb = api.new_user()
    api.fund(admin_headers, a["user_id"], 10 * R)
    assert api.transfer(ha, b["user_id"], 50 * R).status_code == 422  # insufficient balance
    sender = client.get(f"{API}/notifications", headers=ha).json()["items"][0]
    assert sender["type"] == "TRANSFER_FAILED"
    assert "could not be completed" in sender["message"]
    assert "insufficient" not in sender["message"].lower()
    assert client.get(f"{API}/notifications", headers=hb).json()["items"] == []


def test_admin_has_no_notifications(client, admin_headers):
    page = client.get(f"{API}/notifications", headers=admin_headers)
    assert page.status_code == 200 and page.json()["items"] == []
