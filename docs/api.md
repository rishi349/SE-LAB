# API

Base path `/api/v1`. JSON in and out. Interactive docs: `/docs` (Swagger) and `/redoc`;
OpenAPI spec: `/api/v1/openapi.json`.

## Conventions

* **Auth:** `Authorization: Bearer <token>` from `POST /auth/login`. Tokens last 1 hour; no
  refresh tokens — log in again.
* **Money:** `amount_paise` is a JSON integer. `10.5`, `100.0` and `"100"` are rejected (422).
  Responses also include a display string, e.g. `"amount": "1234.56"`.
* **Idempotency:** `POST /transfers` and `POST /admin/fundings` require an
  `Idempotency-Key` header (8–128 chars of `A-Z a-z 0-9 - _`). A replay returns the stored
  result and adds `Idempotent-Replayed: true`.
* **Errors:** always `{"error": {"code": "...", "message": "...", "details": ...}}`.
* **Pagination:** `page` (≥1), `page_size` (1–100, default 20); responses carry
  `pagination: {page, page_size, total_items, total_pages}`.
* **Timestamps:** UTC, ISO-8601 with `Z`.

## Endpoints

| Method & path | Who | Success | Notes |
|---|---|---|---|
| `POST /auth/register` | public | 201 | body `{name, email, password}`; creates user + ₹0 wallet. 409 duplicate email. Rate limited. |
| `POST /auth/login` | public | 200 | `{access_token, token_type, expires_in}`. 401 for any bad credential or deactivated account. Rate limited. |
| `GET /users/me` | any user | 200 | profile incl. `next_name_change_allowed_at` |
| `PATCH /users/me` | any user | 200 | `{name}` only; 409 `NAME_CHANGE_COOLDOWN`; email/user_id/role → 422 |
| `POST /users/me/deletion-request` | ordinary user | 202 | `{password}`; 409 `BALANCE_NOT_SETTLED` unless balance is ₹0 |
| `GET /users/{user_id}` | any user | 200 | recipient lookup → `{user_id, name}`; 404 if not an active user |
| `GET /wallets/me` | any user | 200 | wallet and balance |
| `POST /transfers` | ordinary user | 201 | `{recipient_user_id, amount_paise}`; see below |
| `GET /transactions` | any user | 200 | filters: `status`, `direction`, `from_date`, `to_date` (IST dates, inclusive) |
| `GET /transactions/{id}` | any user | 200 | 404 unless you are sender or recipient |
| `GET /admin/users/{user_id}` | admin | 200 | exact User ID only → `{user_id, name}`. No email search. |
| `POST /admin/fundings` | admin | 201 | `{recipient_user_id, amount_paise}`; 422 `INVALID_AMOUNT`, 404 `USER_NOT_FOUND` |
| `POST /admin/reconciliation-runs` | admin | 201 | runs checks now, returns the full report |
| `GET /admin/reconciliation-runs` | admin | 200 | previous runs, newest first |
| `GET /admin/reconciliation-runs/{run_id}` | admin | 200 | one report with discrepancies |
| `GET /health` | public | 200 | `{"status": "ok"}` |

## Transfer responses

**Success — 201**
```json
{
  "transaction_id": "TXN0K3M8Q2W7Z5R1T9V4",
  "type": "TRANSFER", "status": "SUCCESS", "direction": "OUTGOING",
  "amount_paise": 150000, "amount": "1500.00", "currency": "INR",
  "sender": {"user_id": "USR...", "name": "Asha"},
  "recipient": {"user_id": "USR...", "name": "Ravi"},
  "created_at": "2026-11-19T10:15:30.123456Z"
}
```

**Business failure — 422** (the attempt is recorded; no money moved). The message is the
same for every reason (insufficient balance, limits, self-transfer, unknown recipient,
zero/negative amount):
```json
{"error": {"code": "TRANSFER_FAILED",
           "message": "The transfer could not be completed.",
           "details": {"transaction": {"transaction_id": "TXN...", "status": "FAILED", "...": "..."}}}}
```

**Request rejected before execution — 422 `VALIDATION_ERROR` / `IDEMPOTENCY_KEY_*`**: nothing
is stored and the idempotency key is not consumed.

## Status codes used

200, 201, 202, 401, 403, 404, 405, 409, 422, 429 (with `Retry-After`), 500, 503
(`SERVICE_BUSY` if the database stays locked past the busy timeout).

## Rate limits (per minute)

| Scope | Limit | Keyed by |
|---|---|---|
| register | 5 | client IP |
| login | 10 | client IP |
| transfer | 10 | user |
| recipient lookup | 30 | user |
| profile update | 10 | user |
| account deletion | 5 | user |
| admin funding | 30 | admin |
| reconciliation | 5 | admin |
