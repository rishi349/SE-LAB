# Database

SQLite through Python's built-in `sqlite3`, direct parameterised SQL, no ORM. The full
schema is in [`app/db/schema.sql`](../app/db/schema.sql) and is applied idempotently at
startup (`CREATE ... IF NOT EXISTS`).

Connection settings (`app/db/connection.py`): `PRAGMA foreign_keys = ON`,
`journal_mode = WAL` (readers don't block the writer), `busy_timeout = 10s`, manual
transaction control (`isolation_level=None`).

## Tables

### `users`
| Column | Notes |
|---|---|
| `user_id` TEXT PK | Permanent public ID, e.g. `USR7K2M9Q4XAB`. Trigger blocks changes. |
| `email` TEXT UNIQUE | Lower-cased. Cannot change (trigger); set to NULL only by the purge. |
| `name`, `password_hash` | NULL only after personal-data deletion. |
| `role` | `user` or `admin`. Trigger blocks changes. |
| `status` | `ACTIVE`, `DEACTIVATED`, `DELETED` (account status — wallets have no states). |
| `name_changed_at` | Last successful name change (cooldown anchor). |
| `deactivated_at`, `deletion_due_at`, `personal_data_deleted_at` | Deletion lifecycle. |

### `wallets`
One per user (`user_id UNIQUE`). `balance_paise INTEGER CHECK (typeof = 'integer' AND >= 0)`.
Cannot be deleted (trigger).

### `transactions`
One row per transfer attempt (SUCCESS or FAILED) and per successful admin funding. Written
once with its final status; UPDATE and DELETE are blocked by triggers.

| Column | Notes |
|---|---|
| `type` | `TRANSFER` or `ADMIN_FUNDING` |
| `status` | `SUCCESS` or `FAILED` (admin funding is only ever stored as SUCCESS) |
| `sender_user_id` | Initiator (the admin for funding) |
| `recipient_user_id` | NULL when the recipient was not a valid active user |
| `recipient_ref` | Recipient ID as entered (shown to the sender for unknown recipients) |
| `amount_paise` | Integer; must be > 0 when SUCCESS |
| `failure_code` | Internal reason for FAILED rows. Never returned by any endpoint. |
| `idempotency_key` | `UNIQUE (sender_user_id, idempotency_key)` |

### `ledger_entries`
Immutable (UPDATE/DELETE blocked). `entry_type` DEBIT/CREDIT, `amount_paise > 0`,
`balance_after_paise`, `UNIQUE (transaction_id, entry_type)`.

* Successful transfer → 1 DEBIT (sender wallet) + 1 CREDIT (recipient wallet).
* Successful admin funding → 1 CREDIT (recipient wallet), no DEBIT.
* Failed transfer → no entries.

Invariant: `wallet.balance_paise == SUM(credits) − SUM(debits)` for that wallet.

### `notifications`
In-app notifications (see `docs/notifications-design.md`). Columns: `user_id` (who sees it),
`type` (`TRANSFER_SENT`, `TRANSFER_RECEIVED`, `TRANSFER_FAILED`, `WALLET_FUNDED`),
`transaction_id`, `counterparty_user_id`, `amount_paise`, `is_read`, `created_at`, `read_at`.
`UNIQUE (user_id, transaction_id, type)`. No message text is stored; it is built on read.
Not a financial record: only `is_read`/`read_at` change, and the purge deletes a user's own rows.

### `reconciliation_runs` / `reconciliation_discrepancies`
Stored reports, immutable once written. Status is one of `COMPLETED_CLEAN`,
`COMPLETED_WITH_DISCREPANCIES`, `FAILED` (enforced by CHECK constraints together with
`discrepancy_count`).

## Indexes

* `transactions (sender_user_id, created_at)`, `(recipient_user_id, created_at)` — history.
* `transactions (sender_user_id, type, status, created_at)` — daily-limit sum.
* `ledger_entries (wallet_id)`, `(transaction_id)` — reconciliation.
* `notifications (user_id, created_at)`, `(user_id, is_read)` — list and unread count.

## Timestamps

Stored as fixed-width UTC strings `YYYY-MM-DDTHH:MM:SS.ffffffZ`, so text order equals time
order. Business days (daily limit, history date filters) are IST days converted to UTC
ranges in `app/core/clock.py`.

## Defence in depth for balances

1. Service checks balance under the write lock (`BEGIN IMMEDIATE`).
2. `UPDATE ... WHERE balance_paise >= ?` refuses to overdraw.
3. `CHECK (balance_paise >= 0)` at the table level.
