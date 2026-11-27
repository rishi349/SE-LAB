# Engineering decisions & assumptions

This implementation was built from the **implementation prompt** (the explicit corrections),
without access to the full combined 9-phase design document. Where the prompt was silent,
the choice below was made using standard practice and kept as simple as possible.
**Items marked ⚠ should be checked against the original Phase 1–6 design** and changed if
the design decided differently.

## Followed exactly from the prompt
* Stack: Python 3.12, FastAPI, SQLite via `sqlite3`, direct SQL, no ORM, `/api/v1`, Uvicorn,
  Pytest, Ruff, python-dotenv, JWT HS256 (1 h, no refresh), bcrypt.
* Integer paise; atomic transfers; immutable ledger; debit/credit model.
* Wallet auto-created at registration with ₹0; no wallet endpoint, deletion or freeze.
* Roles `user`/`admin`; admin created explicitly, never via the API; admin cannot create admins.
* Admin funding: no debit of the admin wallet, works at ₹0, no limits, no system account,
  no initial allocation, no cap. Admin search by User ID only (no email search at all).
* ₹50,000 per transfer, ₹1,00,000 successful outgoing per IST day (`Asia/Kolkata`).
* Failed attempts persisted, no money movement, no ledger entries, not counted in limits,
  reason hidden; visible to both parties if recipient valid, sender only otherwise.
* History: newest first, pagination, date/status/direction filters, ownership.
* Deletion: settle balance → deactivate → 7-day wait → personal data deleted; ledger kept.
* Name change once per 60 days; registration does not start the cooldown; email/User ID
  not editable.
* Reconciliation: read-only, unique run ID, stored reports, manual admin trigger, statuses
  `COMPLETED_CLEAN` / `COMPLETED_WITH_DISCREPANCIES` / `FAILED`.
* Notifications not implemented.

## Decisions made where the prompt was silent

| # | Decision | Why |
|---|---|---|
| D1 ⚠ | **Idempotency:** client sends `Idempotency-Key` header (required); key stored on the transaction row with `UNIQUE(sender_user_id, idempotency_key)`; replay returns the stored transaction. No separate idempotency table, no expiry, no payload fingerprinting. | Simplest mechanism that makes duplicate execution impossible at the database level. Prompt forbids fingerprinting unless in the design. |
| D2 ⚠ | **Rejected-request key policy:** a transfer that fails a business rule is stored as FAILED, so its key is consumed (retry returns the same failure). Requests rejected before execution (bad body/header/auth) store nothing and don't consume the key. Rejected admin fundings store nothing. | Follows directly from "failed attempts must be persisted" + "no automatic retry for insufficient balance". |
| D3 ⚠ | **Concurrency:** `BEGIN IMMEDIATE` for every money-moving operation, plus `UPDATE … WHERE balance >= amount` and a `CHECK (balance >= 0)`. | SQLite has one writer; taking the lock before reading balances removes double-spend races without row locks. |
| D4 ⚠ | **Schema** as in `app/db/schema.sql`: `users`, `wallets`, `transactions` (attempts + funding in one table), `ledger_entries`, `reconciliation_runs`, `reconciliation_discrepancies`. | Minimal set that supports every required feature and reconciliation. |
| D5 | Admin funding stored as `type = ADMIN_FUNDING` with a single CREDIT ledger entry; the admin is recorded as `sender_user_id`. | Matches "no debit against the admin wallet" and "no system funding account" while staying auditable. |
| D6 | Admin also gets a ₹0 wallet at creation, which never changes. | Keeps "every user has exactly one wallet" true without special cases. |
| D7 | Admin cannot send or receive ordinary transfers, and cannot be a funding recipient. | Admin is a specialised testing user, not an ordinary user. |
| D8 | Valid recipient = existing, `ACTIVE`, role `user`. Deactivated/deleted accounts and admins are treated like a nonexistent recipient (sender-only visibility). | Deactivated users cannot transfer; avoids revealing admin accounts. |
| D9 ⚠ | User ID format `USR` + 10 Crockford base32 chars, random. | Short, unguessable, unambiguous to read aloud. |
| D10 | `name` is required at registration (needed for search results and history). | Admin search must return name + User ID. |
| D11 ⚠ | Failed transfer → HTTP **422 `TRANSFER_FAILED`** with one generic message for every reason, and the recorded transaction in `error.details`. | Satisfies "do not reveal internal failure reasons" while still giving the client the attempt's ID. |
| D12 | Recipient lookup endpoint `GET /users/{user_id}` returns only ID and name. | Prompt: "User IDs are used … for recipient lookup". |
| D13 ⚠ | Deletion endpoint `POST /users/me/deletion-request` (requires password). No cancellation endpoint because deactivated users cannot log in. | Prompt defines no cancellation; adding one would be a new feature. |
| D14 ⚠ | Purge after 7 days is a script (`scripts/purge_deactivated_accounts.py`), not a background scheduler. | No scheduling infrastructure requested; keeps the monolith simple. |
| D15 | "Legally required retention" interpreted as: keep User ID, wallet row, all transactions and ledger entries; delete name, email, password hash. | Financial records must be preserved; transactions only reference User IDs. |
| D16 | Same-name "change" is a no-op that does not start the cooldown. | Avoids locking a user out for a request that changed nothing. |
| D17 ⚠ | Rate limits (per minute): register 5/IP, login 10/IP, transfer 10/user, lookup 30, profile 10, deletion 5, admin funding 30, reconciliation 5. In-memory. | Prompt requires rate limiting but gives no numbers. |
| D18 | Passwords 8–72 bytes; emails lower-cased; names trimmed, 1–100 chars. | bcrypt's 72-byte limit; standard hygiene. |
| D19 | History `from_date`/`to_date` are inclusive **IST** calendar dates. | Users and the daily limit both think in IST days. |
| D20 | Reconciliation adds a system-wide check: Σ wallet balances = Σ successful admin funding. | Money only enters via funding, so this catches any leak; it is a read-only check. |
| D21 | Reconciliation runs synchronously inside the `POST` request. | Dataset is small; no job queue requested. |
| D22 | Database triggers enforce immutability of transactions, ledger entries and reports, and permanence of `user_id`, `role`, `email`, wallets and users. | Immutability enforced even against buggy code, not just by convention. |
| D23 | Token expiry fixed at 1 hour in code (not configurable). | Finalised value; prevents accidental drift through env vars. |
| D24 | Run with `uvicorn app.main:create_app --factory`. | Lets tests build apps with their own settings/database. |
| D25 | Added a demo client at `/demo` (one static HTML/JS file, `/` redirects to it) at the team's request, for demonstrations and manual testing. | It only calls the public `/api/v1` endpoints, is excluded from the OpenAPI spec, and adds no backend rules. All validation, limits, idempotency and authorization remain enforced by the API. Served from the same origin, so no CORS change was needed. |

## Known limitations
* Rate limits are per process and reset on restart.
* SQLite allows one writer at a time; fine for this project's load.
* API-layer tests were written against FastAPI's `TestClient`; run `pytest` after
  installing `requirements-dev.txt` (CI does this automatically).
