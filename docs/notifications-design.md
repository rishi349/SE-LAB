# Notifications — Design (Phase 10)

Status: **Implemented** · Adds a feature that was "out of scope for now" in the original design.
Logged as decision **D26** in `docs/decisions.md` once agreed.

## 1. Goal

Tell users, inside the app, when something happens to their money: money sent, money
received, a transfer that failed, and money added by the admin.

## 2. Scope

**In scope**
- In-app notifications stored in SQLite and shown on the demo page (bell icon + unread count).
- Four events (section 4).
- List, unread count, mark one as read, mark all as read.

**Out of scope**
- Email, SMS and push notifications (need external services and secrets).
- Real-time delivery (WebSockets/SSE) and background polling. The count updates on page
  load, after actions and when the bell is opened.
- Notification settings/preferences.
- Deleting notifications: users can only view them and mark them as read.
- Admin notifications: the admin receives none.

## 3. Rules (must not break the original design)

| # | Rule | Why |
|---|---|---|
| N1 | A notification is written **only after** the money transaction has committed, in its own short DB transaction. | "Financial transaction success must not depend on notifications." |
| N2 | If writing a notification fails, the error is logged (no personal data) and ignored. The API response is unchanged. | Same as N1. |
| N3 | Notifications never show internal failure reasons. | Failed attempts must not reveal why they failed. |
| N4 | Users can see and change only their own notifications. Others' IDs return 404. | Ownership / privacy. |
| N5 | An idempotent replay creates **no** new notification. | Retries must not look like new payments. |
| N6 | Notifications are not financial records: no ledger entries, no balance changes, not checked by reconciliation. | Keeps the ledger model untouched. |
| N7 | Messages are built when read, from stored fields, using the counterparty's **current** name. | A deleted user's name never lingers inside old messages. |

## 4. Events

| Type | When | Who gets it | Message shown |
|---|---|---|---|
| `TRANSFER_SENT` | Transfer succeeded | Sender | You sent ₹1,000.00 to Ravi. |
| `TRANSFER_RECEIVED` | Transfer succeeded | Recipient | You received ₹1,000.00 from Asha. |
| `TRANSFER_FAILED` | Transfer attempt recorded as FAILED | Sender only | Your transfer of ₹1,000.00 could not be completed. |
| `WALLET_FUNDED` | Admin funding succeeded | Funded user | ₹5,000.00 was added to your wallet. |

Notes
- A failed attempt still appears in **both** users' transaction history (unchanged rule);
  only the sender gets a notification, to avoid noise.
- If the counterparty's personal data has been deleted, the name shows as "a deleted user".

## 5. Data model

```sql
CREATE TABLE IF NOT EXISTS notifications (
    notification_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id               TEXT NOT NULL REFERENCES users (user_id),   -- who sees it
    type                  TEXT NOT NULL CHECK (type IN
                          ('TRANSFER_SENT', 'TRANSFER_RECEIVED', 'TRANSFER_FAILED', 'WALLET_FUNDED')),
    transaction_id        TEXT NOT NULL REFERENCES transactions (transaction_id),
    counterparty_user_id  TEXT REFERENCES users (user_id),            -- NULL for WALLET_FUNDED
    amount_paise          INTEGER NOT NULL CHECK (typeof(amount_paise) = 'integer'),
    is_read               INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
    created_at            TEXT NOT NULL,
    read_at               TEXT,
    UNIQUE (user_id, transaction_id, type)                            -- never twice for one event
);

CREATE INDEX IF NOT EXISTS idx_notif_user_created ON notifications (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_notif_user_unread  ON notifications (user_id, is_read);
```

- No message text is stored (rule N7); the API builds it.
- `UNIQUE (user_id, transaction_id, type)` is a second guard for rule N5.
- Only `is_read` / `read_at` ever change. No delete except the 7-day purge (section 8).

## 6. Flow

```
POST /transfers
  └─ execute_transfer()
       ├─ BEGIN IMMEDIATE … COMMIT        (money moves or FAILED row is stored — unchanged)
       └─ if not replayed:
            notify_transfer(txn)          (new, own transaction, wrapped in try/except)
                SUCCESS → TRANSFER_SENT (sender) + TRANSFER_RECEIVED (recipient)
                FAILED  → TRANSFER_FAILED (sender)
  └─ response (same as today)

POST /admin/fundings
  └─ fund_wallet() … COMMIT
       └─ if not replayed: notify WALLET_FUNDED (recipient), try/except
```

## 7. API (prefix `/api/v1`, JWT required, any role)

| Method & path | Success | Notes |
|---|---|---|
| `GET /notifications` | 200 | `page`, `page_size` (1–100), `unread_only` (bool). Newest first. Returns `items` + `pagination` + `unread_count`. |
| `GET /notifications/unread-count` | 200 | `{"unread_count": 3}`. |
| `GET /wallets/me` (existing) | 200 | Now also returns `unread_notifications` (piggybacked). |
| `PATCH /notifications/{notification_id}/read` | 200 | Marks one as read; returns it. 404 if not yours. Already-read is fine (no error). |
| `POST /notifications/read-all` | 200 | `{"updated": 5}` |

Example item:
```json
{
  "notification_id": 42,
  "type": "TRANSFER_RECEIVED",
  "message": "You received ₹1,000.00 from Asha.",
  "amount_paise": 100000,
  "transaction_id": "TXN0K3M8Q2W7Z5R1T9V4",
  "is_read": false,
  "created_at": "2026-11-27T08:15:30.123456Z"
}
```
Errors use the existing envelope `{"error": {"code", "message", "details"}}`.

## 8. Account deletion

When the 7-day purge deletes a user's personal data, their notifications are deleted too.
Notifications *about* them in other users' lists stay, and show "a deleted user" (rule N7).

## 9. Frontend (demo page)

- Bell icon with an unread badge in the top bar, for logged-in users.
- Click → dropdown with the latest 10 notifications, unread ones highlighted, "Mark all read".
- Clicking a notification marks it read.
- **No timer / no polling.** The badge count updates:
  - on page load and after every send action, from `unread_notifications` included in the
    `GET /wallets/me` response (piggybacking — no extra request);
  - when the bell is opened (the list response includes `unread_count`).
- Real-time delivery (WebSockets / Server-Sent Events, or a transactional outbox + message
  queue) is the documented next step, not part of this version.

## 10. Load from the 30-second check

Each logged-in user with the page visible sends about **2 requests per minute**.

| Users with the page open | Requests per second |
|---|---|
| 10 (class demo) | ~0.3 |
| 1,000 | ~33 |
| 10,000 | ~330 |
| 1,00,000 | ~3,300 |

Each request is a JWT check, one user lookup and one indexed `COUNT`, so a single
FastAPI + SQLite process handles the first rows easily. SQLite in WAL mode lets these reads run
alongside transfers without blocking them.

How the design keeps the load low:
- The check pauses when the browser tab is hidden and stops on logout.
- It returns only one number, not the full list.
- The full list is loaded only when the bell is opened.

**Known limitation:** this approach does not suit very large numbers of users. At that scale a
real system would push updates instead of asking (Server-Sent Events or WebSockets), cache the
counts, or check less often. That is out of scope for this project and recorded here so the
trade-off is explicit.

## 11. Code changes

| Area | Change |
|---|---|
| `app/db/schema.sql` | Add the `notifications` table and indexes. |
| `app/modules/notifications/` | New module: `service.py`, `router.py`, `schemas.py`. |
| `app/modules/transfers/service.py` | Call the notifier after commit (not on replay). |
| `app/modules/admin/service.py` | Same, for funding. |
| `app/modules/users/service.py` | Purge also deletes the user's notifications. |
| `app/modules/wallets/` | Wallet response includes `unread_notifications`. |
| `app/core/money.py` | `format_inr()` for messages (₹1,00,000.00 style). |
| `app/main.py` | Register the notifications router. |
| `app/static/demo.html` | Bell, badge, dropdown. |

## 12. Tests

- Each event creates the right notifications for the right users (sender, recipient, funded user).
- A failed transfer gives a sender-only notification whose message contains no failure reason.
- Replaying an idempotency key creates no extra notification.
- A notifier error does not change the transfer result or the balances.
- Users cannot read or mark others' notifications (404).
- Unread count, `unread_only`, pagination and newest-first order.
- Mark one / mark all read; marking twice is harmless.
- After purge, the user's notifications are gone and others see "a deleted user".
- Reconciliation is still clean after transfers with notifications.

## 13. Documentation updates

- `README.md`: remove notifications from "Out of scope", add the new endpoints.
- `docs/api.md`, `docs/database.md`, `docs/financial-flows.md` (one line on rule N1).
- `docs/decisions.md`: add **D26**.
- Obsidian: new note `Notifications.md`, link from `Home.md`.
