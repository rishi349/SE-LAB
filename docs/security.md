# Security

## Authentication
* Email + password; passwords hashed with **bcrypt** (cost from `BCRYPT_ROUNDS`, default 12).
  Passwords must be 8+ characters and at most 72 bytes (bcrypt's limit) — longer input is
  rejected rather than silently truncated.
* Login failures return one generic `INVALID_CREDENTIALS` message for wrong password,
  unknown email or deactivated account. Unknown emails still run a bcrypt check so response
  time does not reveal whether an email is registered.
* **JWT access tokens**, HS256, 1-hour expiry, no refresh tokens. Claims: `sub`, `role`,
  `type=access`, `iat`, `exp`. `alg: none` and other algorithms are rejected.
* `JWT_SECRET` comes from the environment and must be at least 32 characters; the app
  refuses to start otherwise.

## Authorization
* Role and status are read **from the database on every request**; the token's `role`
  claim is never trusted on its own. A deactivated user's still-valid token stops working.
* `require_admin` guards every `/admin/*` route; `require_ordinary_user` guards transfers
  and self-deletion.
* Ownership: history queries always filter by the caller; fetching someone else's
  transaction returns 404 (same as nonexistent, so IDs cannot be probed).
* Privilege escalation is blocked at three layers: registration schema forbids extra fields
  (no `role`), there is no API to create admins or change roles, and a database trigger
  rejects any `UPDATE` of `users.role`.
* Admin is created only with `python -m scripts.create_admin` (password from
  `ADMIN_PASSWORD` or an interactive prompt — never a CLI argument).

## Data privacy
* Admin search is by exact User ID only and returns just `user_id` and `name`. There is no
  email search of any kind.
* Recipient lookup returns only `user_id` and `name`.
* Internal transfer failure reasons are stored but never returned.
* Validation errors never echo submitted values (passwords cannot leak into responses).
* Account deletion removes name, email and password hash after 7 days; financial records
  keep only the permanent User ID.

## Input handling
* Pydantic models with `extra="forbid"`; amounts are strict integers; IDs are pattern-checked.
* All SQL is parameterised. The only dynamic SQL is the history `WHERE` clause, assembled
  from fixed fragments with named parameters.

## Rate limiting
In-memory sliding window per IP (register, login) or per user (transfers, lookup, profile
update, deletion, admin funding, reconciliation). `429` with `Retry-After`. See
[api.md](api.md#rate-limits-per-minute). Limits are per process and reset on restart —
acceptable for this single-instance deployment.

## Secrets & logging
* `.env` is git-ignored; `.env.example` holds placeholders only.
* CI runs **gitleaks** over the full history and fails if a `.env` file is tracked.
* Request logs contain method, path, status and duration only — no headers, tokens, bodies
  or passwords. Unhandled errors log the exception server-side and return a generic 500.

## Database integrity as a security control
Immutability triggers on `transactions`, `ledger_entries` and reconciliation reports;
`CHECK` constraints keep balances non-negative integers; foreign keys are enforced.
