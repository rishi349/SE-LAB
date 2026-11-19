# Architecture

## Style: modular monolith

One FastAPI process, one SQLite file, code split into feature modules with a fixed
internal shape:

```
modules/<feature>/
  router.py    HTTP only: parse request, call service, shape response
  service.py   business rules + SQL; no FastAPI imports
  schemas.py   Pydantic request/response models
```

Services never import FastAPI, so the business logic is testable without HTTP and the
same functions are reused by scripts (`create_admin`, `purge_deactivated_accounts`).

```
              ┌──────────────── FastAPI app (app/main.py) ────────────────┐
 HTTP ──────▶ │ routers ──▶ deps (auth, roles, rate limit, DB connection) │
              │    │                                                       │
              │    ▼                                                       │
              │ services: auth · users · wallets · transfers · admin ·     │
              │           transactions · reconciliation                    │
              │    │                                                       │
              │    ▼                                                       │
              │ ledger service (only code that changes balances)           │
              └────┬───────────────────────────────────────────────────────┘
                   ▼
            SQLite (WAL, foreign keys ON, CHECK constraints, immutability triggers)
```

## Module responsibilities

| Module | Responsibility |
|---|---|
| `auth` | registration (user + wallet atomically), admin creation (script only), login/JWT |
| `users` | profile view/edit, 60-day name cooldown, recipient lookup, deactivation, 7-day purge |
| `wallets` | wallet view |
| `ledger` | idempotency lookup, writing transaction rows, debit/credit with ledger entries |
| `transfers` | transfer validation, limits, failed-attempt recording |
| `transactions` | history, filters, pagination, ownership checks, public transaction view |
| `admin` | user search by User ID, wallet funding |
| `reconciliation` | read-only integrity checks and stored reports |

## Cross-cutting pieces (`app/core`)

* `errors.py` — typed errors mapped to one JSON envelope by `handlers.py`.
* `deps.py` — per-request DB connection, current user (role and status re-read from the
  database on every request), `require_admin`, `require_ordinary_user`, rate limits.
* `security.py` — bcrypt hashing, HS256 JWT with 1-hour expiry.
* `money.py`, `clock.py`, `ids.py`, `validators.py`, `idempotency.py`.

## Demo client

`app/static/demo.html` is a single static page served at `/demo`. It is a thin client: it
calls the same `/api/v1` endpoints as any other client, stores the JWT in `sessionStorage`,
generates a fresh `Idempotency-Key` per action (with a "retry same request" button to show
idempotency), and converts rupee input to integer paise without floating-point maths. It has no
privileges of its own; the backend enforces every rule.

## Request lifecycle (transfer)

1. `deps` opens a connection, validates the JWT, loads the user, checks role and rate limit.
2. Pydantic validates the body (strict integer paise); the router validates `Idempotency-Key`.
3. `transfers.service.execute_transfer` runs everything inside `BEGIN IMMEDIATE`.
4. Router returns `201` (success) or `422 TRANSFER_FAILED` (attempt recorded, no money moved).
5. The connection closes; the middleware logs method, path, status and timing only.

## Phase dependency order used for implementation

1. Structure/config → 2. Database schema → 3. Auth & authorization → 4. Financial
transactions (ledger, transfers, admin funding, idempotency) → 5. API (profile, history,
deletion) → 6. Reconciliation → 7. Tests → 8. CI → 9. Documentation.
